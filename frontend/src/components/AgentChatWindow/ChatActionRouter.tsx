import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useGlobalFilters } from "../../hooks/useGlobalFilters";
import type { ActionPayload } from "../../types/agent";

const PAGE_TO_ROUTE: Record<string, string> = {
  overview: "/overview",
  analysis: "/analysis",
  compare: "/compare",
  "cross-benchmark": "/cross-benchmark",
  config: "/config",
  "error-analysis": "/analysis",
  "version-compare": "/compare",
};

interface ChatActionRouterProps {
  action: ActionPayload | null;
  onHandled?: () => void;
}

export function ChatActionRouter({ action, onHandled }: ChatActionRouterProps) {
  const navigate = useNavigate();
  const { setFilter } = useGlobalFilters();

  useEffect(() => {
    if (!action) {
      return;
    }

    switch (action.type) {
      case "navigate": {
        const nextRoute = PAGE_TO_ROUTE[action.page];
        if (nextRoute) {
          navigate(nextRoute);
        }
        break;
      }
      case "set_filter":
        setFilter(action.key, action.value);
        break;
      case "highlight_record":
        window.dispatchEvent(
          new CustomEvent("agent:highlight_record", {
            detail: { record_id: action.record_id },
          }),
        );
        break;
      case "open_session":
        window.dispatchEvent(
          new CustomEvent("agent:open_session", {
            detail: { session_id: action.session_id },
          }),
        );
        navigate("/overview");
        break;
    }

    onHandled?.();
  }, [action, navigate, onHandled, setFilter]);

  return null;
}
