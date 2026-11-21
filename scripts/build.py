#!/usr/bin/env python3
import re
from pathlib import Path
from tempfile import NamedTemporaryFile


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")


def read_ad_rules(path, template):
    protected = []
    for line in template.partition("{{AD_RULES}}")[0].splitlines():
        fields = line.split(",")
        if len(fields) == 3 and fields[0] in {"DOMAIN", "DOMAIN-SUFFIX"}:
            kind, domain, policy = fields
            if policy in {"PROXY", "DIRECT"}:
                protected.append((kind, domain))

    rules = []
    seen = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        kind, separator, domain = line.partition(",")
        if kind not in {"DOMAIN", "DOMAIN-SUFFIX"} or not separator or not DOMAIN.fullmatch(domain):
            raise ValueError(f"Invalid ad rule on line {number}")
        for protected_kind, protected_domain in protected:
            if (
                domain == protected_domain
                or (kind == "DOMAIN-SUFFIX" and protected_domain.endswith("." + domain))
                or (protected_kind == "DOMAIN-SUFFIX" and domain.endswith("." + protected_domain))
            ):
                raise ValueError(f"Ad rule on line {number} overlaps a protected host")
        if line not in seen:
            seen.add(line)
            rules.append(line)
    if not 0 < len(rules) <= 500 or len("\n".join(rules).encode("utf-8")) + 1 > 50 * 1024:
        raise ValueError("Ad list is empty or exceeds 500 rules / 50 KiB")
    return rules


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        temp.write(content)
    temporary_path = Path(temp.name)
    try:
        temporary_path.chmod(0o644)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_public(root, output):
    template = (root / "config/surf.conf.in").read_text(encoding="utf-8")
    rules = read_ad_rules(root / "rules/ads.list", template)
    ad_rules = "\n".join(f"{rule},REJECT" for rule in rules)
    assets = {
        "go1f-surf.conf": template.replace("{{AD_RULES}}", ad_rules),
        "ads.list": "\n".join(rules) + "\n",
    }
    for module in sorted((root / "modules").glob("splash-*.srmodule")):
        assets[f"modules/{module.name}"] = module.read_text(encoding="utf-8")
    for name, content in assets.items():
        write_file(output / name, content)


if __name__ == "__main__":
    try:
        build_public(ROOT, ROOT / "dist")
    except ValueError as error:
        raise SystemExit(f"Build failed: {error}") from error
    print("Built public assets in dist/")
