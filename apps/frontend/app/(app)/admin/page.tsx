"use client";

import { useQuery } from "@tanstack/react-query";
import { adminApi, marketplaceApi, observabilityApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function AdminPage() {
  const { data: users = [] } = useQuery({ queryKey: ["admin-users"], queryFn: adminApi.users });
  const { data: metrics } = useQuery({ queryKey: ["metrics"], queryFn: observabilityApi.metrics });
  const { data: stats } = useQuery({ queryKey: ["exec-stats"], queryFn: observabilityApi.stats });
  const { data: listings = [] } = useQuery({ queryKey: ["admin-listings"], queryFn: marketplaceApi.listings });

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Requests</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">{metrics?.total_requests ?? 0}</CardContent>
        </Card>
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Error Rate</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">{metrics?.error_requests ?? 0}</CardContent>
        </Card>
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Executions</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">{stats?.executions ?? 0}</CardContent>
        </Card>
      </div>

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">User Management</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user: any) => (
                <TableRow key={user.id}>
                  <TableCell>{user.id}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>{user.role || "user"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Marketplace Listings</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {listings.map((listing: any) => (
                <TableRow key={listing.id}>
                  <TableCell>{listing.id}</TableCell>
                  <TableCell>{listing.agent?.name || "Listing"}</TableCell>
                  <TableCell>${listing.price}</TableCell>
                  <TableCell>{listing.is_active ? "active" : "paused"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
