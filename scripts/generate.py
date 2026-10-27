#!/usr/bin/env python3
"""Call only the daily-writing Skill, using a validated scoring result."""
import sys
from skill_runner import stage_main

if __name__=='__main__': sys.exit(stage_main('daily'))
