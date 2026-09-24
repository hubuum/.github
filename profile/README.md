# Hubuum

**Bring scattered operational data together—without forcing it into somebody else's model.**

[![Hubuum release](https://img.shields.io/github/v/release/hubuum/hubuum?label=server)](https://github.com/hubuum/hubuum/releases)
[![Server CI](https://github.com/hubuum/hubuum/actions/workflows/ci.yml/badge.svg)](https://github.com/hubuum/hubuum/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/hubuum/hubuum/blob/main/LICENSE)

Hubuum is an open-source, flexible asset management platform. It gives teams one
place to collect, structure, relate, search, and govern data from the systems
they already trust—through a consistent REST API, a web console, a CLI, and
typed client libraries.

[Explore Hubuum](https://hubuum.github.io/) · [Server documentation](https://hubuum.github.io/hubuum/)

## Why Hubuum?

- **Model your world.** Define classes for your own domains, optionally validate
  object data with JSON Schema, and organize everything in hierarchical
  collections.
- **Keep existing sources authoritative.** Bring facts in from specialized
  systems instead of replacing them, then connect records with typed relations.
- **Query one interface.** Search and filter nested JSON, traverse relationships,
  calculate derived fields, and automate imports, exports, and reports through
  one REST API.
- **Govern centrally.** Apply collection-scoped permissions, use human or service
  identities, and retain audit and resource history.
- **Operate it your way.** Run native binaries or multi-architecture containers,
  from a single host to horizontally scaled deployments backed by PostgreSQL.

## The project

| Repository | What it provides | Documentation |
| --- | --- | --- |
| [Hubuum Server](https://github.com/hubuum/hubuum) | The Rust REST service, OpenAPI contract, deployment guides, and container images. | [Server guides](https://hubuum.github.io/hubuum/) |
| [Hubuum Frontend](https://github.com/hubuum/hubuum-frontend) | A secure, horizontally scalable web console built with Next.js. | [Frontend guides](https://hubuum.github.io/hubuum-frontend/) |
| [Hubuum CLI](https://github.com/hubuum/hubuum-cli) | Interactive, one-shot, and scripted terminal workflows. | [CLI guides](https://hubuum.github.io/hubuum-cli/) |
| [Rust client](https://github.com/hubuum/hubuum-client-rust) | Sync and async typed clients, fluent queries, pagination, and task helpers. | [Rust guides](https://hubuum.github.io/hubuum-client-rust/) |
| [Python client](https://github.com/hubuum/hubuum-client-python) | Sync and async typed clients with Pydantic models and complete OpenAPI coverage. | [Python guides](https://hubuum.github.io/hubuum-client-python/) |

**Published platforms:** Server archives for Linux, macOS, and Windows, plus
Linux container images for AMD64 and ARM64. CLI binaries for Linux x86_64/ARM64,
Apple Silicon macOS, and Windows x86_64.

## Get started

1. Open the [server documentation](https://hubuum.github.io/hubuum/)
   for its latest released installation and administration guides.
2. Choose the deployment guide in that edition
   for Docker or Podman Compose, or download a native binary from
   [GitHub Releases](https://github.com/hubuum/hubuum/releases).
3. Add the [web console](https://github.com/hubuum/hubuum-frontend), or automate
   Hubuum with the [CLI](https://github.com/hubuum/hubuum-cli),
   [Rust client](https://github.com/hubuum/hubuum-client-rust), or
   [Python client](https://github.com/hubuum/hubuum-client-python).

> [!IMPORTANT]
> Hubuum is pre-1.0 software. It is ready for evaluation and early deployments,
> but APIs and configuration may change. Pin deployments and clients to explicit,
> compatible versions.

## Join in

Hubuum is MIT-licensed and developed in the open. Start with the
[server documentation](https://hubuum.github.io/hubuum/), browse the
[OpenAPI contract](https://github.com/hubuum/hubuum/blob/main/docs/openapi.json),
or [open an issue](https://github.com/hubuum/hubuum/issues) with a question or idea.

_Hubuum (𒄷𒁍𒌝) means “axle” or “wheel assembly” in Sumerian—a fitting name for
the shared hub between your data sources and the tools that use them._
