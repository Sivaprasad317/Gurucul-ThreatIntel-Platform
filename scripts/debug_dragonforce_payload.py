from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


HTML_FILE = Path("dragonforce_debug.html")


class DevalueDecoder:
    """Resolve Nuxt/Devalue reference-table payloads."""

    def __init__(self, values: list[Any]) -> None:
        self.values = values
        self.cache: dict[int, Any] = {}
        self.resolving: set[int] = set()

    def resolve(self, index: int) -> Any:
        """Resolve a reference from the Devalue table."""
        if not isinstance(index, int):
            return index

        if index < 0 or index >= len(self.values):
            raise IndexError(
                f"Invalid Devalue reference {index}; "
                f"payload contains {len(self.values)} entries."
            )

        if index in self.cache:
            return self.cache[index]

        if index in self.resolving:
            # Keep circular references from crashing the diagnostic.
            return self.values[index]

        self.resolving.add(index)

        try:
            raw = self.values[index]
            result = self._resolve(raw)
            self.cache[index] = result
            return result
        finally:
            self.resolving.discard(index)

    def _resolve(self, value: Any) -> Any:
        """Recursively resolve dictionaries and arrays."""
        if isinstance(value, dict):
            result = {}

            for key, ref in value.items():
                # Dictionary keys in this payload are ordinary strings.
                if isinstance(ref, int):
                    result[key] = self.resolve(ref)
                else:
                    result[key] = ref

            return result

        if isinstance(value, list):
            if not value:
                return []

            # Nuxt reactive wrappers.
            if (
                isinstance(value[0], str)
                and value[0] in {
                    "Reactive",
                    "ShallowReactive",
                    "Readonly",
                    "ShallowReadonly",
                }
            ):
                if len(value) >= 2 and isinstance(value[1], int):
                    return self.resolve(value[1])

                # A malformed/empty wrapper should not crash debugging.
                return None

            # Special Devalue types.
            #
            # We don't actually need to reconstruct these for finding
            # the DragonForce publication records.
            if isinstance(value[0], str) and value[0] in {
                "Set",
                "Map",
                "Date",
                "URL",
            }:
                if len(value) >= 2 and isinstance(value[1], int):
                    return self.resolve(value[1])

                return []

            # Ordinary Devalue array.
            return [
                self.resolve(item)
                if isinstance(item, int)
                else item
                for item in value
            ]

        return value


def load_payload() -> list[Any]:
    """Load the largest application/json script from the saved page."""
    html = HTML_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(html, "html.parser")

    scripts = soup.find_all(
        "script",
        attrs={"type": "application/json"},
    )

    if not scripts:
        raise RuntimeError(
            "No <script type='application/json'> payload found."
        )

    script = max(
        scripts,
        key=lambda item: len(item.get_text()),
    )

    payload = json.loads(script.get_text())

    if not isinstance(payload, list):
        raise TypeError(
            f"Expected payload list, got {type(payload).__name__}"
        )

    return payload


def find_victims(value: Any) -> list[dict[str, Any]]:
    """Find company/publication records in the decoded payload."""
    victims: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            required = {
                "uuid",
                "created_at",
                "name",
                "website",
                "address",
                "description",
            }

            if required.issubset(node):
                victims.append(node)

            for child in node.values():
                walk(child)

        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)

    return victims


def main() -> None:
    """Decode the saved DragonForce page and inspect records."""
    payload = load_payload()

    print(f"Raw payload entries: {len(payload)}")

    decoder = DevalueDecoder(payload)

    # The Nuxt payload root is entry 0.
    root = decoder.resolve(0)

    print(f"Decoded root type: {type(root).__name__}")

    victims = find_victims(root)

    print(f"Victim records found: {len(victims)}")
    print()

    for victim in victims[:20]:
        description = victim.get("description") or ""

        print("=" * 70)
        print(f"NAME:        {victim.get('name')}")
        print(f"WEBSITE:     {victim.get('website')}")
        print(f"ADDRESS:     {victim.get('address')}")
        print(f"UUID:        {victim.get('uuid')}")
        print(f"DESCRIPTION: {description[:250]}")


if __name__ == "__main__":
    main()