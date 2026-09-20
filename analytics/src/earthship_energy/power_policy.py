"""Explicit, secret-free activation policy; never guesses a physical table ID."""
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from .inventory import SourceResolutionError, item_table_name
from .power_evidence import utc, unique
from .power_store import POLICY


@dataclass(frozen=True)
class PowerEvidencePolicy:
    cutover: datetime
    item_name: str = 'Power_Evidence_JSON'

    def resolve_table(self, items, tables):
        ids = [item_id for item_id, name in items if name == self.item_name]
        if len(ids) != 1:
            raise SourceResolutionError('power evidence Item missing or ambiguous')
        table = item_table_name(ids[0])
        if table not in tables:
            raise SourceResolutionError('power evidence persistence table missing')
        return table


def load_power_policy(path):
    try:
        with Path(path).open('rb') as handle:
            raw = handle.read(4097)
        if len(raw) > 4096:
            raise ValueError('power policy exceeds size budget')
        payload = json.loads(raw, object_pairs_hook=unique)
        if (not isinstance(payload, dict)
                or set(payload) != {'version','policy','item_name','cutover'}
                or type(payload['version']) is not int or payload['version'] != 1
                or payload['policy'] != POLICY or payload['item_name'] != 'Power_Evidence_JSON'
                or not isinstance(payload['cutover'], str)):
            raise ValueError('invalid power policy schema')
        return PowerEvidencePolicy(utc(datetime.fromisoformat(payload['cutover'])))
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        raise ValueError('cannot load valid power evidence policy') from exc
