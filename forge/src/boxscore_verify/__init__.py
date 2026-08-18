"""The §22 verifier: four layers, each able to reject on its own, sharing no code with the generator.

The solver exists twice in this repository and that is deliberate. `boxscore_forge` has one so the
erasure knows when to stop; this package has its own so the result is confirmed by something that
did not produce it. Factoring out the common parts would put a single bug on both sides of the check
and turn the guarantee into theatre. See §22.
"""
