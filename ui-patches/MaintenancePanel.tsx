import { useState } from "react";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent } from "@nous-research/ui/ui/components/card";
import { RefreshCw, RotateCw, ShieldCheck } from "lucide-react";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";

export function MaintenancePanel() {
  const [loading, setLoading] = useState(false);
  const { showToast } = useToast();

  const runMaintenance = async (action: string) => {
    setLoading(true);
    try {
      await api.post(`/api/maintenance/${action}`);
      showToast(`Maintenance action '${action}' triggered`, "success");
    } catch (e) {
      showToast(`Action failed: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="fixed bottom-4 left-4 z-50 w-64 shadow-lg">
      <CardContent className="p-3 flex flex-col gap-2">
        <h4 className="font-mondwest text-xs font-bold uppercase tracking-wider text-muted-foreground">System Maintenance</h4>
        <Button size="sm" ghost className="justify-start gap-2" onClick={() => void runMaintenance("update")}>
          <RefreshCw className="h-3.5 w-3.5" /> Update Hermes
        </Button>
        <Button size="sm" ghost className="justify-start gap-2" onClick={() => void runMaintenance("restart")}>
          <RotateCw className="h-3.5 w-3.5" /> Restart Gateway
        </Button>
        <Button size="sm" ghost className="justify-start gap-2" onClick={() => void runMaintenance("patch")}>
          <ShieldCheck className="h-3.5 w-3.5" /> Re-apply Context Fix
        </Button>
      </CardContent>
    </Card>
  );
}
