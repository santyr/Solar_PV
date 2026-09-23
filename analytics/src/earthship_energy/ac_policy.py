"""Explicit inverter-only topology policy for separate AC evidence.

No production policy is installed here. A complete site-local day is eligible
only within both the real evidence cutover and the operator-attested topology
period. This does not turn inverter output into unconditional household load.
"""
from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path

from .ac_reader import read_ac_history
from .inventory import SourceResolutionError, item_table_name
from .power_evidence import unique, utc
from .series import local_day_bounds

POLICY = 'qualified_inverter_ac_output_v1'
ITEM = 'Inverter_AC_Evidence_JSON'
BASIS = 'inverter_only_no_bypass_or_generator'


@dataclass(frozen=True)
class AcEvidencePolicy:
    cutover: datetime
    topology_from: datetime
    topology_until: datetime | None
    item_name: str = ITEM

    def resolve_table(self, items, tables):
        ids = [item_id for item_id, name in items if name == self.item_name]
        if len(ids) != 1:
            raise SourceResolutionError('AC evidence Item missing or ambiguous')
        table = item_table_name(ids[0])
        if table not in tables:
            raise SourceResolutionError('AC evidence persistence table missing')
        return table

    def day_window(self, local_date, *, as_of):
        """Require a complete finished local day within the confirmed period."""
        if type(local_date) is not date:
            raise ValueError('site-local date required')
        as_of = utc(as_of)
        start, end = local_day_bounds(local_date, 'America/Denver')
        if (start < self.cutover or start < self.topology_from or end > as_of
                or (self.topology_until is not None and end > self.topology_until)):
            raise ValueError('day is outside qualified AC evidence or topology period')
        return start, end

    def read_day(self, settings, table_name, local_date, *, as_of):
        """Read intervals only; accounting and publication are separate gates."""
        start, end = self.day_window(local_date, as_of=as_of)
        return read_ac_history(settings, table_name, start, end,
                               cutover=self.cutover,
                               topology_start=self.topology_from,
                               topology_end=end)


def load_ac_policy(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise ValueError('AC policy exceeds size budget')
        data = json.loads(raw, object_pairs_hook=unique)
        if (not isinstance(data, dict) or set(data) != {
                'version', 'policy', 'item_name', 'cutover', 'topology'
            } or type(data['version']) is not int or data['version'] != 1
                or data['policy'] != POLICY or data['item_name'] != ITEM
                or not isinstance(data['cutover'], str)):
            raise ValueError('invalid AC policy schema')
        topology = data['topology']
        if (not isinstance(topology, dict) or set(topology) != {
                'basis', 'effective_from', 'effective_until'
            } or topology['basis'] != BASIS
                or not isinstance(topology['effective_from'], str)
                or topology['effective_until'] is not None
                and not isinstance(topology['effective_until'], str)):
            raise ValueError('invalid AC topology schema')
        cutover = utc(datetime.fromisoformat(data['cutover']))
        start = utc(datetime.fromisoformat(topology['effective_from']))
        until = (utc(datetime.fromisoformat(topology['effective_until']))
                 if topology['effective_until'] is not None else None)
        if start < cutover or until is not None and until <= start:
            raise ValueError('AC topology period predates evidence or is empty')
        return AcEvidencePolicy(cutover, start, until)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        raise ValueError('cannot load valid AC evidence policy') from exc
