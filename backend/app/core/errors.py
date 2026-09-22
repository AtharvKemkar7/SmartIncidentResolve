KUBECTL_MISSING = (
    "Unable to connect to Kubernetes cluster.\n\n"
    "Please verify:\n"
    "- kubectl is installed\n"
    "- kubeconfig path\n"
    "- cluster access\n"
    "- kubectl permissions"
)

CLUSTER_UNREACHABLE = (
    "Unable to connect to Kubernetes cluster.\n\n"
    "Please verify:\n"
    "- kubeconfig path\n"
    "- cluster access\n"
    "- kubectl permissions"
)

MISSING_KUBECONFIG = (
    "No kubeconfig was found.\n\n"
    "Please verify:\n"
    "- kubeconfig path\n"
    "- cluster access\n"
    "- kubectl permissions"
)

OPENROUTER_FAILURE = (
    "AI reasoning is temporarily unavailable. "
    "A local diagnosis was generated from collected evidence."
)

AUTH_REQUIRED = "Please log in to investigate clusters and view history."
AUTH_INVALID = "Invalid email or password."


def friendly_kubectl_error(error: str | None) -> str:
    text = (error or "").lower()
    if "not installed" in text or "not on path" in text:
        return KUBECTL_MISSING
    if "kubeconfig" in text or "config" in text:
        return MISSING_KUBECONFIG
    if "timeout" in text or "refused" in text or "unreachable" in text or "forbidden" in text:
        return CLUSTER_UNREACHABLE
    return CLUSTER_UNREACHABLE
