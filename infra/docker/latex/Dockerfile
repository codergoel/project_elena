# Minimal LaTeX toolchain for local PDF experiments (checkpoint 1.2).
# Compose profile `latex` only — not started by default.
FROM debian:bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    texlive-latex-base \
  && rm -rf /var/lib/apt/lists/*

# Default verifies the install; override in Compose with a long-running command.
CMD ["pdflatex", "--version"]
