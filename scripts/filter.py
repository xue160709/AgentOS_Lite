#!/usr/bin/env python3
"""Call the scoring/filtering Skill, independently of collection and writing."""
import sys
from skill_runner import stage_main

if __name__=='__main__': sys.exit(stage_main('filter'))
