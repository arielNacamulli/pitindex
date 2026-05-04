"""Tests for the Click CLI."""

from __future__ import annotations

import json

from click.testing import CliRunner

from pitindex.cli import cli


def test_cli_help():
    r = CliRunner().invoke(cli, ["--help"])
    assert r.exit_code == 0
    assert "pitindex" in r.output


def test_cli_version():
    r = CliRunner().invoke(cli, ["--version"])
    assert r.exit_code == 0


def test_cli_info_table():
    r = CliRunner().invoke(cli, ["info"])
    assert r.exit_code == 0
    assert "build_timestamp_utc" in r.output
    assert "current_size" in r.output


def test_cli_info_json():
    r = CliRunner().invoke(cli, ["info", "--format", "json"])
    assert r.exit_code == 0
    payload = json.loads(r.output)
    assert payload["current_size"] > 450
    assert "build_timestamp_utc" in payload


def test_cli_get_table():
    r = CliRunner().invoke(cli, ["get", "--as-of", "2020-12-22"])
    assert r.exit_code == 0
    assert "TSLA" in r.output
    assert "AAPL" in r.output


def test_cli_get_tickers_only():
    r = CliRunner().invoke(cli, ["get", "--as-of", "2020-12-22", "--tickers-only"])
    assert r.exit_code == 0
    tickers = r.output.strip().split("\n")
    assert "TSLA" in tickers
    assert "AAPL" in tickers
    assert len(tickers) > 450


def test_cli_get_csv():
    r = CliRunner().invoke(cli, ["get", "--as-of", "2020-12-22", "--format", "csv"])
    assert r.exit_code == 0
    lines = r.output.strip().split("\n")
    assert lines[0].startswith("ticker,name,cik,gics_sector,gics_sub_industry")


def test_cli_get_json():
    r = CliRunner().invoke(cli, ["get", "--as-of", "2020-12-22", "--format", "json"])
    assert r.exit_code == 0
    payload = json.loads(r.output)
    assert any(row["ticker"] == "TSLA" for row in payload)


def test_cli_get_rejects_future_date():
    r = CliRunner().invoke(cli, ["get", "--as-of", "2099-12-31"])
    assert r.exit_code != 0
    assert "future" in r.output.lower()


def test_cli_history_csv():
    r = CliRunner().invoke(cli, ["history", "--start", "2020-12-01", "--end", "2020-12-31"])
    assert r.exit_code == 0
    lines = r.output.strip().split("\n")
    assert lines[0].startswith("as_of,ticker,name,cik,gics_sector,gics_sub_industry")


def test_cli_history_rejects_inverted_window():
    r = CliRunner().invoke(cli, ["history", "--start", "2020-12-31", "--end", "2020-01-01"])
    assert r.exit_code != 0


def test_cli_subcommands_listed():
    r = CliRunner().invoke(cli, ["--help"])
    for cmd in ("info", "get", "history", "update", "build"):
        assert cmd in r.output
