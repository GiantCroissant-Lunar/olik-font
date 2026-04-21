from dataclasses import dataclass
from typing import List, Optional, Any, Dict, TypeVar, Callable, Type, cast
from datetime import datetime
import dateutil.parser


T = TypeVar("T")


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False


def from_datetime(x: Any) -> datetime:
    return dateutil.parser.parse(x)


def from_dict(f: Callable[[Any], T], x: Any) -> Dict[str, T]:
    assert isinstance(x, dict)
    return { k: f(v) for (k, v) in x.items() }


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


@dataclass
class Entry:
    components: List[str]
    """Sub-character identifiers. Empty when atomic. May include numeric IDs for characters that
    don't have Unicode codepoints.
    """
    operator: Optional[str] = None
    """cjk-decomp operator: lowercase letter(s) like 'a', 'c', 'b', 's', 'd', 'o', 't', 'ra',
    'str', 'r3tr', 'd/t'. null means atomic.
    """

    @staticmethod
    def from_dict(obj: Any) -> 'Entry':
        assert isinstance(obj, dict)
        components = from_list(from_str, obj.get("components"))
        operator = from_union([from_none, from_str], obj.get("operator"))
        return Entry(components, operator)

    def to_dict(self) -> dict:
        result: dict = {}
        result["components"] = from_list(from_str, self.components)
        result["operator"] = from_union([from_none, from_str], self.operator)
        return result


@dataclass
class Source:
    commit: str
    license: str
    upstream: str
    retrieved_at: Optional[datetime] = None

    @staticmethod
    def from_dict(obj: Any) -> 'Source':
        assert isinstance(obj, dict)
        commit = from_str(obj.get("commit"))
        license = from_str(obj.get("license"))
        upstream = from_str(obj.get("upstream"))
        retrieved_at = from_union([from_datetime, from_none], obj.get("retrieved_at"))
        return Source(commit, license, upstream, retrieved_at)

    def to_dict(self) -> dict:
        result: dict = {}
        result["commit"] = from_str(self.commit)
        result["license"] = from_str(self.license)
        result["upstream"] = from_str(self.upstream)
        if self.retrieved_at is not None:
            result["retrieved_at"] = from_union([lambda x: x.isoformat(), from_none], self.retrieved_at)
        return result


@dataclass
class CJKDecomp:
    """Structured JSON form of the cjk-decomp dataset (https://github.com/amake/cjk-decomp).
    Each entry maps a character to its operator + components per cjk-decomp's grammar. Atomic
    characters have operator: null and components: [].
    """
    entries: Dict[str, Entry]
    """Character → decomposition entry. Keys are single Unicode CJK characters."""

    schema_version: str
    """Schema version of THIS file (not upstream data)."""

    source: Source

    @staticmethod
    def from_dict(obj: Any) -> 'CJKDecomp':
        assert isinstance(obj, dict)
        entries = from_dict(Entry.from_dict, obj.get("entries"))
        schema_version = from_str(obj.get("schema_version"))
        source = Source.from_dict(obj.get("source"))
        return CJKDecomp(entries, schema_version, source)

    def to_dict(self) -> dict:
        result: dict = {}
        result["entries"] = from_dict(lambda x: to_class(Entry, x), self.entries)
        result["schema_version"] = from_str(self.schema_version)
        result["source"] = to_class(Source, self.source)
        return result


def cjk_decomp_from_dict(s: Any) -> CJKDecomp:
    return CJKDecomp.from_dict(s)


def cjk_decomp_to_dict(x: CJKDecomp) -> Any:
    return to_class(CJKDecomp, x)
