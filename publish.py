#!/usr/bin/env python3
import sys
import subprocess

if not input("did you remember to update Josh_Wolfe_resume.pdf? [yN] ").lower().startswith("y"):
  print("interpreting answer as 'no'")
  sys.exit(1)

for item in [
    "index.html",
    "resume/",
    "site/",
  ]:
  cmd = ["rsync", "-vuza", item, "server:public_http/" + item]
  print(" ".join(cmd))
  subprocess.check_call(cmd)

  cmd = ["ssh", "server", "find", "public_http/" + item, "-type", "f", "-exec", "chmod", "-R", "+r", "{}", "+"]
  print(" ".join(cmd))
  subprocess.check_call(cmd)
