"""Lector propio y producto mensual. No importa engine ni loaders."""
import json
import csv
import re
from html.parser import HTMLParser
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

from ..config import Blocked, shift_month


def recalculate(raw_path: Path, cutoff: date, months: int) -> Decimal:
    raw = json.loads(raw_path.read_bytes())
    observations = {}
    for row in raw["observations"]:
        key = date.fromisoformat(row["date"])
        if key in observations:
            raise Blocked("INDEPENDENT_DUPLICATE")
        observations[key] = (Decimal(row["quota"]), Decimal(row["uf"]))
    with localcontext() as ctx:
        ctx.prec = 40
        value = Decimal(1)
        for offset in range(-months + 1, 1):
            prev = shift_month(cutoff, offset - 1)
            end = shift_month(cutoff, offset)
            if prev not in observations or end not in observations:
                raise Blocked("INDEPENDENT_GAP")
            qi, ui = observations[prev]
            qj, uj = observations[end]
            value *= (qj / qi) * (ui / uj)
        return value - 1


def compare(expected: Decimal, actual: Decimal):
    # Cerca de cero, error absoluto <= 1e-30; fuera de cero, relativo <= 1e-9.
    if abs(expected - actual) > max(abs(expected) * Decimal("1e-9"), Decimal("1e-30")):
        raise Blocked("INDEPENDENT_MISMATCH")


class _UFTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=False;self.cell=False;self.rows=[];self.row=[];self.buffer=""

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="table" and (attrs.get("id")=="table_export" or attrs.get("class")=="tabla"):
            self.active=True
        if self.active and tag=="tr":self.row=[]
        if self.active and tag in ("td","th"):
            self.cell=True;self.buffer=""

    def handle_data(self,data):
        if self.cell:self.buffer+=data

    def handle_endtag(self,tag):
        if self.active and tag in ("td","th") and self.cell:
            self.row.append(self.buffer.strip());self.cell=False
        if self.active and tag=="tr":self.rows.append(self.row)
        if self.active and tag=="table":self.active=False


class IndependentSystem:
    """Lectores propios; producto por AFP y suma al final, sin agregado encadenado."""
    def __init__(self,csv_path:Path,uf_files):
        self.days={};self.uf={};names=None;confirmed=False
        def number(s):return Decimal(s.strip().replace(".","").replace(",","."))
        for row in csv.reader(csv_path.read_bytes().decode("latin-1").splitlines(),delimiter=";"):
            if not row:continue
            if row[0]=="Valores Confirmados":confirmed=True;names=None;continue
            if row[0].startswith("Valores Provisorios"):confirmed=False;names=None;continue
            if row[0]=="Fecha":names={x.strip():i for i,x in enumerate(row) if i and x.strip()};continue
            if not confirmed or names is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",row[0]):continue
            d=date.fromisoformat(row[0]);record={}
            for afp,i in names.items():
                if row[i].strip() and row[i+1].strip():
                    record[afp]=(number(row[i]),number(row[i+1]))
            if d in self.days:raise Blocked("INDEPENDENT_DUPLICATE")
            self.days[d]=record
        for year,path in uf_files:
            raw=path.read_bytes()
            try:text=raw.decode("utf-8")
            except UnicodeDecodeError:text=raw.decode("latin-1")
            parser=_UFTable();parser.feed(text)
            for row in parser.rows:
                if len(row)!=13 or not row[0].isdigit():continue
                for month,value in enumerate(row[1:],1):
                    if value:
                        d=date(year,month,int(row[0]))
                        if d in self.uf:raise Blocked("INDEPENDENT_DUPLICATE_UF")
                        self.uf[d]=number(value)

    def return_for(self,start,end):
        dates=[start]
        current=shift_month(start,1)
        while current<=end:
            dates.append(current);current=shift_month(current,1)
        if dates[-1]!=end or any(d not in self.days or d not in self.uf for d in dates):
            raise Blocked("INDEPENDENT_GAP")
        weights_date=shift_month(end,-1)
        if weights_date not in self.days:raise Blocked("INDEPENDENT_WEIGHTS_MISSING")
        active={a:values[1] for a,values in self.days[weights_date].items() if values[1]>0}
        eligible=[];excluded=[]
        for afp in sorted(active):
            if afp not in self.days[end]:raise Blocked("INDEPENDENT_ACTIVE_AFP_MISSING")
            if all(afp in self.days[d] and self.days[d][afp][0]>0 for d in dates):eligible.append(afp)
            elif start<min(d for d,values in self.days.items() if afp in values):excluded.append(afp)
            else:raise Blocked("INDEPENDENT_AFP_HISTORY_GAP")
        if not eligible:raise Blocked("INDEPENDENT_NO_HISTORY")
        with localcontext() as ctx:
            ctx.prec=40
            total=sum((active[a] for a in eligible),Decimal(0))
            result=Decimal(0)
            for afp in eligible:
                product=Decimal(1)
                for left,right in zip(dates,dates[1:]):
                    product*=self.days[right][afp][0]/self.days[left][afp][0]*self.uf[left]/self.uf[right]
                result+=active[afp]*(product-1)
            result/=total
        return dict(real=result,included_afps=eligible,excluded_afps=excluded)
