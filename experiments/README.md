# Experiments

Raw calibration and trial artifacts are immutable. A runner must atomically
reserve a trial directory before any provider call and must persist terminal
metadata for success, transport failure, malformed output, refusal, timeout, and
enforcement failure.
