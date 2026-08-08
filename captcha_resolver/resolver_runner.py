#!/usr/bin/env python3
"""
Resolver Runner - Chay resolver tren cung console
"""
import sys
import os

# Them path de import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from captcha_resolver.resolver import run_resolver_standalone

if __name__ == "__main__":
    run_resolver_standalone()