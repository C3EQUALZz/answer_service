# Security Policy

## Supported versions

`answer_service` is pre-1.0. Only the `master` branch receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Report it privately through GitHub's
[private vulnerability reporting](https://github.com/C3EQUALZz/answer_service/security/advisories/new),
or by email to <dan.kovalev2013@gmail.com>.

Include, as far as you can:

- what an attacker can do, and what access they need to do it
- the affected component (HTTP route, worker task, adapter)
- a reproduction — a request, an uploaded file, or a failing test

You can expect an acknowledgement within 7 days and an assessment within 30.

## Scope

Especially relevant for this service:

- **Uploaded source files.** CSV and Excel uploads are parsed by the worker.
  Anything that turns a crafted file into code execution, an unbounded
  allocation, or a read outside the staging directory is in scope.
- **Prompt and retrieval boundaries.** Content from an indexed catalog reaching
  a model as instruction rather than data.
- **Credential exposure.** The Mistral, Qdrant, Postgres and NATS credentials
  are marked as secret fields in the config loaders precisely so a startup
  failure never logs them; a path that leaks one is in scope.
- **Error responses.** 5xx messages are masked before they reach a client. A
  route that returns a host name, a table name or a query is in scope.

Out of scope: findings that require an already-compromised host, denial of
service by volume alone, and reports produced by a scanner without a
demonstrated impact.
