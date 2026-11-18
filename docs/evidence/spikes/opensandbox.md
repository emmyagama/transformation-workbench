# Spike evidence: OpenSandbox

**Status: BLOCKED â€” documentation inspected; no hands-on run.** Date inspected:
2026-11-18. This is a truthful blocker card, not an evaluation result.

## Why it was considered

OpenSandbox is a sandbox lifecycle project for isolated agent workloads. A
narrow trial could test whether a future tool execution path can be placed in a
separate, deny-by-default environment instead of the invoking host.

## Official sources inspected

- AKS + Kata example:
  <https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/examples/aks-kata.md>
- Repository: <https://github.com/opensandbox-group/OpenSandbox>

The inspected example requires:

- an AKS cluster with the `kata-vm-isolation` runtime class;
- Helm 3 and `kubectl`;
- Python 3.10+ with `pip install opensandbox requests`;
- an Azure OpenAI resource and credentials for the example LLM step;
- container images and cluster networking.

## Environment probe

```powershell
Get-Command opensandbox, docker, podman -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -c "import importlib.util; print(importlib.util.find_spec('opensandbox'))"
```

```text
opensandbox=not_found
python=3.11.9
docker=not_found
podman=not_found
```

The example also uses an LLM endpoint. That would be a hosted model operation,
outside the demonstration boundary, even if the cluster and package were
available.

## What was actually done

- Read the official AKS + Kata walkthrough and prerequisites.
- Confirmed the package, cluster runtime, container runtime, and credentials are
  absent.
- Did not install the package, create a cluster, pull images, or call a model.

## Fit assessment

**Not demonstrated.** OpenSandbox is a plausible isolation layer for a future
write-capable tool, but this review produced no sandbox, no isolation test, and
no credential-path test. Do not describe it as integrated or validated.

## What would unblock it

With explicit approval, a disposable environment, and a non-production model
path:

1. Create an isolated cluster and install pinned OpenSandbox components.
2. Deploy the smallest official sample with no real credentials.
3. Run one benign command and one denied network call.
4. Confirm that the Workbench path is not given arbitrary host access.
5. Record the runtime class, policy, versions, output, and teardown.

## Boundary

No cloud resource, real credential, real data, or hosted model call was used.
