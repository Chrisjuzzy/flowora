"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { walletApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useState } from "react";

export default function WalletPage() {
  const { data: wallet, refetch: refetchWallet } = useQuery({
    queryKey: ["wallet"],
    queryFn: walletApi.balance,
  });
  const { data: transactions = [], refetch: refetchTx } = useQuery({
    queryKey: ["transactions"],
    queryFn: walletApi.transactions,
  });
  const { data: charges = [], refetch: refetchCharges } = useQuery({
    queryKey: ["walletCharges"],
    queryFn: walletApi.charges,
  });
  const [amount, setAmount] = useState(25);
  const [pendingCharge, setPendingCharge] = useState<any | null>(null);

  const rechargeMutation = useMutation({
    mutationFn: () => walletApi.recharge(amount),
    onSuccess: () => {
      refetchWallet();
      refetchTx();
      refetchCharges();
    },
  });

  const confirmMutation = useMutation({
    mutationFn: (chargeId: number) => walletApi.confirmRecharge(chargeId),
    onSuccess: () => {
      setPendingCharge(null);
      refetchWallet();
      refetchTx();
      refetchCharges();
    },
  });

  const failMutation = useMutation({
    mutationFn: (chargeId: number) => walletApi.failRecharge(chargeId),
    onSuccess: () => {
      setPendingCharge(null);
      refetchCharges();
    },
  });

  return (
    <div className="grid gap-8 lg:grid-cols-[1.2fr_1fr]">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Wallet Balance</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-4xl font-semibold">${wallet?.balance ?? 0}</p>
          <p className="text-sm text-muted">Currency: {wallet?.currency ?? "USD"}</p>
        </CardContent>
      </Card>

      <Card className="app-surface h-fit">
        <CardHeader>
          <CardTitle className="heading-serif">Recharge Credits</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            type="number"
            min="1"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
          />
          <Button
            className="w-full"
            onClick={() =>
              rechargeMutation.mutate(undefined, {
                onSuccess: (data: any) => {
                  setPendingCharge(data);
                },
              })
            }
          >
            Create Recharge Request
          </Button>
          {pendingCharge && (
            <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-xs text-muted">
              <p>Charge {pendingCharge.charge_id} is {pendingCharge.status}.</p>
              <p>Confirm to simulate payment and credit your wallet.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() => confirmMutation.mutate(pendingCharge.charge_id)}
                >
                  Confirm Payment
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => failMutation.mutate(pendingCharge.charge_id)}
                >
                  Mark Failed
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="app-surface lg:col-span-2">
        <CardHeader>
          <CardTitle className="heading-serif">Transaction History</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transactions.map((tx: any) => (
                <TableRow key={tx.id}>
                  <TableCell>{tx.type}</TableCell>
                  <TableCell>{tx.amount}</TableCell>
                  <TableCell>{tx.description}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="app-surface lg:col-span-2">
        <CardHeader>
          <CardTitle className="heading-serif">Recharge Requests</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Reference</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {charges.map((charge: any) => (
                <TableRow key={charge.id}>
                  <TableCell>{charge.status}</TableCell>
                  <TableCell>{charge.amount}</TableCell>
                  <TableCell>{charge.provider_reference}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
