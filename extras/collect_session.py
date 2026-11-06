#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Experimental: collect this machine's running-client session parameters.

This helper is OPTIONAL and intentionally kept outside the main package.
It reads the client process's own runtime request URLs, extracts the session
parameters that the client itself generated, and writes them to a local JSON
file that the main tool can consume via --credentials.

Strict boundaries:
  * Personal device and personal account only.
  * Respect the platform's terms of service. No high-frequency or bulk requests.
  * Session parameters expire within hours. Never commit or log the output.
  * No credentials, machine paths, account ids or personal data are hardcoded here.

Supported: Windows desktop client 4.x. All process names and paths are
discovered at runtime; nothing about a specific machine is embedded.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import subprocess
import sys
import time

PROCESS_NAMES = ("Weixin.exe", "WeChatAppEx.exe")
URL_RE = re.compile(rb"https?://mp\.weixin\.qq\.com/[A-Za-z0-9_\-\.?=&/%#;+:~]{15,3000}")
PARAM_RE = re.compile(rb"([A-Za-z_]+)=([^&]+)")
REQUIRED = ("key", "uin", "pass_ticket", "appmsg_token")
OPTIONAL = ("wxtoken",)

MAX_REGION = 80 * 1024 * 1024
READABLE_PROTECT = (0x02, 0x04, 0x20, 0x40)
MEM_COMMIT = 0x1000
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64),
        ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", wt.DWORD),
        ("_a1", wt.DWORD),
        ("RegionSize", ctypes.c_uint64),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
        ("_a2", wt.DWORD),
    ]


def _kernel():
    if sys.platform != "win32":
        raise RuntimeError("This helper only runs on Windows.")
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE
    k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_uint64,
                                 ctypes.POINTER(MBI), ctypes.c_size_t]
    k.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.c_void_p,
                                    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    return k


def discover_pids():
    """Find client processes by name at runtime; no hardcoded pids."""
    wanted = {n.lower() for n in PROCESS_NAMES}
    r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True)
    text = r.stdout.decode("gbk", "replace")
    pids = []
    for line in text.splitlines():
        m = re.match(r'"([^"]+)","(\d+)"', line)
        if m and m.group(1).lower() in wanted:
            pids.append(int(m.group(2)))
    return pids


def parse_credentials(url_bytes):
    """Extract one credential set from a client request URL, or return None."""
    params = {k.decode("ascii", "ignore"): v.decode("ascii", "replace")
              for k, v in PARAM_RE.findall(url_bytes)}
    if not all(k in params for k in REQUIRED):
        return None
    out = {k: params[k] for k in REQUIRED}
    for k in OPTIONAL:
        out[k] = params.get(k, "")
    return out


def iter_regions(k, handle):
    addr = 0
    while addr < 0x7FFFFFFFFFFF:
        info = MBI()
        if k.VirtualQueryEx(handle, ctypes.c_uint64(addr),
                            ctypes.byref(info), ctypes.sizeof(info)) == 0:
            break
        if info.RegionSize == 0:
            break
        if (info.State == MEM_COMMIT and info.Protect in READABLE_PROTECT
                and 0 < info.RegionSize < MAX_REGION):
            yield info.BaseAddress, info.RegionSize
        addr = info.BaseAddress + info.RegionSize


def collect(timeout=60):
    """Return a de-duplicated list of candidate credential sets."""
    k = _kernel()
    pids = discover_pids()
    if not pids:
        raise RuntimeError("No client process found. Please launch and sign in first.")

    found, start, scanned = {}, time.time(), 0
    for pid in pids:
        handle = k.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                               False, pid)
        if not handle:
            continue
        try:
            for base, size in iter_regions(k, handle):
                if time.time() - start > timeout:
                    break
                buf = ctypes.create_string_buffer(size)
                read = ctypes.c_size_t(0)
                if not k.ReadProcessMemory(handle, ctypes.c_uint64(base), buf,
                                           size, ctypes.byref(read)):
                    continue
                data = buf.raw[:read.value]
                scanned += len(data)
                for m in URL_RE.finditer(data):
                    cred = parse_credentials(m.group())
                    if cred:
                        found.setdefault(cred["key"], cred)
        finally:
            k.CloseHandle(handle)
        if time.time() - start > timeout:
            break
    print("Scanned %d process(es), %.1f MB, found %d candidate set(s)." %
          (len(pids), scanned / 1048576.0, len(found)))
    return list(found.values())


def verify(creds, biz):
    """Ask the main package which candidate set actually works."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "src"))
    try:
        from wechat_biz_archive.history import probe
    except ImportError:
        print("Main package not importable; skipping verification.")
        return
    good, _ = probe(creds, biz)
    if good:
        print("Verification: at least one candidate set is currently valid.")
    else:
        print("Verification: all candidates rejected (no session). "
              "Open the account page in the client and try again.")


def self_test():
    sample = (b"https://mp.weixin.qq.com/s?__biz=EXAMPLE&mid=1&idx=1&sn=abc"
              b"&key=deadbeef&uin=TEST%3D%3D&pass_ticket=TOKEN%3D%3D"
              b"&appmsg_token=AAtz%252Bfake&wxtoken=777")
    cred = parse_credentials(sample)
    assert cred is not None, "failed to parse required parameters"
    assert cred["key"] == "deadbeef"
    assert cred["appmsg_token"] == "AAtz%252Bfake"
    assert parse_credentials(b"https://example.com/?a=1") is None
    print("self-test: OK (no process was touched)")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="credentials.json",
                   help="local output path (git-ignored, never commit)")
    p.add_argument("--biz", default="",
                   help="optional __biz to probe candidate validity")
    p.add_argument("--timeout", type=int, default=60,
                   help="scan time budget in seconds")
    p.add_argument("--self-test", action="store_true",
                   help="test URL parsing only, without touching any process")
    args = p.parse_args(argv)

    if args.self_test:
        self_test()
        return 0

    try:
        creds = collect(timeout=args.timeout)
    except RuntimeError as e:
        print("Error: %s" % e, file=sys.stderr)
        return 2
    if not creds:
        print("No session parameters found. See docs/SESSION_PROVIDER.md.",
              file=sys.stderr)
        return 3

    out = os.path.abspath(args.out)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"credentials": creds}, f, ensure_ascii=False, indent=2)
    print("Written: %s" % out)
    print("This file is git-ignored. Do NOT commit, paste or share it; "
          "delete it after use.")

    if args.biz:
        verify(creds, args.biz)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
