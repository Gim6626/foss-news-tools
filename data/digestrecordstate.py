from enum import Enum

class DigestRecordState(Enum):
    UNKNOWN = 'unknown'
    IN_DIGEST = 'in_digest'
    OUTDATED = 'outdated'
    DUPLICATE = 'duplicate'
    IGNORED = 'ignored'

DIGEST_RECORD_STATE_VALUES = [state.value for state in DigestRecordState]
