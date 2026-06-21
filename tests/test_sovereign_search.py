"""Network-free tests for the sovereign_search fallback layer."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sovereign_search as S


def _fake(tag, items):
    """Make a provider that returns `items` rows tagged with engine=tag."""
    def prov(query, n):
        return [{"title": f"{tag}-{i}", "url": f"https://{tag}.test/{i}",
                 "snippet": query, "engine": tag} for i in range(min(items, n))]
    return prov


def _boom(_q, _n):
    raise RuntimeError("provider down")


class TestSovereignSearch(unittest.TestCase):
    def setUp(self):
        self._orig = dict(S._PROVIDERS)
        for k in ("SOVEREIGN_SEARCH_ORDER", "SOVEREIGN_SEARCH_URL",
                  "MOJEEK_API_KEY", "BRAVE_API_KEY"):
            os.environ.pop(k, None)

    def tearDown(self):
        S._PROVIDERS.clear()
        S._PROVIDERS.update(self._orig)

    def test_first_nonempty_wins(self):
        S._PROVIDERS.update({"searxng": _fake("searxng", 3), "mojeek": _fake("mojeek", 3),
                             "qwant": _fake("qwant", 3), "ddg": _fake("ddg", 3)})
        r = S.sovereign_search("q", 5)
        self.assertTrue(r["ok"])
        self.assertEqual(r["engine"], "searxng")          # earliest in chain wins
        self.assertEqual(r["results"][0]["engine"], "searxng")

    def test_falls_through_empty_providers(self):
        S._PROVIDERS.update({"searxng": _fake("searxng", 0), "mojeek": _fake("mojeek", 0),
                             "qwant": _fake("qwant", 2), "ddg": _fake("ddg", 3)})
        r = S.sovereign_search("q", 5)
        self.assertEqual(r["engine"], "qwant")            # first two empty -> qwant
        self.assertIn("searxng:0", r["tried"])
        self.assertIn("mojeek:0", r["tried"])

    def test_errors_are_caught_and_chain_continues(self):
        S._PROVIDERS.update({"searxng": _boom, "mojeek": _boom,
                             "qwant": _boom, "ddg": _fake("ddg", 2)})
        r = S.sovereign_search("q", 5)
        self.assertTrue(r["ok"])
        self.assertEqual(r["engine"], "ddg")              # survives 3 crashing tiers
        self.assertTrue(any("err(" in t for t in r["tried"]))

    def test_all_fail_returns_ok_false_never_raises(self):
        S._PROVIDERS.update({k: _boom for k in S._PROVIDERS})
        r = S.sovereign_search("q", 5)
        self.assertFalse(r["ok"])
        self.assertEqual(r["results"], [])
        self.assertIsNone(r["engine"])

    def test_order_override(self):
        S._PROVIDERS.update({"searxng": _fake("searxng", 3), "qwant": _fake("qwant", 3)})
        r = S.sovereign_search("q", 5, order="qwant,searxng")
        self.assertEqual(r["engine"], "qwant")            # explicit order beats default

    def test_env_order_respected(self):
        S._PROVIDERS.update({"searxng": _fake("searxng", 3), "ddg": _fake("ddg", 3)})
        os.environ["SOVEREIGN_SEARCH_ORDER"] = "ddg,searxng"
        try:
            r = S.sovereign_search("q", 5)
            self.assertEqual(r["engine"], "ddg")
        finally:
            os.environ.pop("SOVEREIGN_SEARCH_ORDER", None)

    def test_n_caps_results(self):
        S._PROVIDERS.update({"searxng": _fake("searxng", 50)})
        r = S.sovereign_search("q", 3, order="searxng")
        self.assertEqual(len(r["results"]), 3)

    def test_normalised_shape(self):
        S._PROVIDERS.update({"searxng": _fake("searxng", 1)})
        r = S.sovereign_search("hello", 1, order="searxng")
        row = r["results"][0]
        self.assertEqual(set(row), {"title", "url", "snippet", "engine"})
        self.assertEqual(row["snippet"], "hello")

    def test_web_search_alias(self):
        # stub the whole chain so the alias never touches the network
        S._PROVIDERS.update({"searxng": _fake("searxng", 0), "brave": _fake("brave", 0),
                             "mojeek": _fake("mojeek", 0), "qwant": _fake("qwant", 0),
                             "ddg": _fake("ddg", 2)})
        r = S.web_search("q", 2)
        self.assertTrue(r["ok"])
        self.assertEqual(r["engine"], "ddg")

    def test_brave_in_default_chain_after_searxng(self):
        # default order is searxng,brave,mojeek,qwant,ddg — brave wins if searxng empty
        S._PROVIDERS.update({"searxng": _fake("searxng", 0), "brave": _fake("brave", 3),
                             "mojeek": _fake("mojeek", 3)})
        r = S.sovereign_search("q", 5)
        self.assertEqual(r["engine"], "brave")
        self.assertIn("searxng:0", r["tried"])

    def test_brave_keyless_returns_empty(self):
        # real _brave with no BRAVE_API_KEY must no-op (no network), chain continues
        S._PROVIDERS.update({"qwant": _fake("qwant", 2)})
        r = S.sovereign_search("q", 5, order="brave,qwant")
        self.assertEqual(r["engine"], "qwant")
        self.assertIn("brave:0", r["tried"])

    def test_unknown_provider_names_ignored(self):
        S._PROVIDERS.update({"qwant": _fake("qwant", 2)})
        r = S.sovereign_search("q", 5, order="bogus,qwant")
        self.assertEqual(r["engine"], "qwant")


if __name__ == "__main__":
    unittest.main(verbosity=2)
