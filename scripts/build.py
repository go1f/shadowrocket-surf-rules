#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
REPOSITORY = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-]{0,38}/[a-zA-Z0-9_.-]+")
EXCLUDED_REGION_LABEL = re.compile(r"香港|🇭🇰|hong[ -_]?kong|(?<![a-z])hk(?![a-z])", re.I)
ALLOWED_REGIONS = {"JP", "SG", "US"}
RESERVED_NODE_NAMES = {"chatgpt", "常规代理", "direct", "proxy", "tailscale", "select", "url-test", "fallback", "load-balance", "random"}


def read_ad_rules(path, template):
    protected = []
    for line in template.splitlines():
        fields = line.split(",")
        if len(fields) == 3 and fields[0] in {"DOMAIN", "DOMAIN-SUFFIX"}:
            kind, domain, policy = fields
            if policy == "ChatGPT" or (policy == "DIRECT" and kind == "DOMAIN"):
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


def select_nodes(profile):
    if not isinstance(profile, dict) or set(profile) != {"exclude_labels", "verified_nodes"}:
        raise ValueError("Private profile must contain exclude_labels and verified_nodes")
    labels = profile["exclude_labels"]
    nodes = profile["verified_nodes"]
    if not isinstance(labels, list) or any(not isinstance(label, str) or not label.strip() for label in labels):
        raise ValueError("Invalid private exclusion labels")
    if not isinstance(nodes, list):
        raise ValueError("verified_nodes must be a list")

    eligible = []
    seen = set()
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {"name", "exit_region"}:
            raise ValueError("Each private node requires name and exit_region")
        name, region = node["name"], node["exit_region"]
        if not isinstance(name, str) or not name or name != name.strip() or not name.isprintable():
            raise ValueError("Invalid private node name")
        if (
            any(char in name for char in ",;=#[]{}")
            or "://" in name
            or name.upper().startswith("REJECT")
            or name.casefold() in RESERVED_NODE_NAMES
        ):
            raise ValueError("A private node name contains a reserved token or delimiter")
        if name.casefold() in seen:
            raise ValueError("Duplicate private node name")
        seen.add(name.casefold())
        if not isinstance(region, str):
            raise ValueError("Invalid exit_region")
        if region in ALLOWED_REGIONS and not EXCLUDED_REGION_LABEL.search(name) and not any(
            label.casefold() in name.casefold() for label in labels
        ):
            eligible.append(name)
    return eligible


def render_config(template, rules, repository=None, nodes=()):
    if repository:
        if not REPOSITORY.fullmatch(repository) or repository.split("/")[1] in {".", ".."}:
            raise ValueError("Repository must use owner/repo format")
        ad_rules = f"RULE-SET,https://raw.githubusercontent.com/{repository}/release/ads.list,REJECT"
    else:
        ad_rules = "\n".join(f"{rule},REJECT" for rule in rules)
    members = "".join("," + node for node in nodes)
    return template.replace("{{PROXY_MEMBERS}}", members).replace("{{AD_RULES}}", ad_rules)


def write_file(path, content, *, private=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        temp.write(content)
    temporary_path = Path(temp.name)
    try:
        if not private:
            temporary_path.chmod(0o644)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_public(root, output, repository=None):
    template = (root / "config/surf.conf.in").read_text(encoding="utf-8")
    rules = read_ad_rules(root / "rules/ads.list", template)
    assets = {
        "surf.conf": render_config(template, rules, repository),
        "surf-offline.conf": render_config(template, rules),
        "ads.list": "\n".join(rules) + "\n",
    }
    for module in sorted((root / "modules").glob("splash-*.srmodule")):
        assets[f"modules/{module.name}"] = module.read_text(encoding="utf-8")
    for name, content in assets.items():
        write_file(output / name, content)


def main():
    parser = argparse.ArgumentParser(description="Build Shadowrocket configuration files.")
    parser.add_argument("--repository", help="owner/repo for the remote ad rule set")
    parser.add_argument("--personal", action="store_true", help="build only .private/surf.conf")
    args = parser.parse_args()
    try:
        if args.personal:
            try:
                profile = json.loads((ROOT / ".private/profile.json").read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise ValueError("Cannot read .private/profile.json") from None
            nodes = select_nodes(profile)
            template = (ROOT / "config/surf.conf.in").read_text(encoding="utf-8")
            rules = read_ad_rules(ROOT / "rules/ads.list", template)
            config = render_config(template, rules, args.repository, nodes)
            write_file(ROOT / ".private/surf.conf", config, private=True)
            print(f"Built .private/surf.conf with {len(nodes)} eligible nodes")
        else:
            build_public(ROOT, ROOT / "dist", args.repository)
            print("Built public assets in dist/")
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
