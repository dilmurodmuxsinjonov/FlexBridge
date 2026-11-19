"use client";

import AccountSecurityWorkspace from "@/components/security/AccountSecurityWorkspace";

export default function UniversalAccountSettingsPage() {
  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-6 pb-16">
      <AccountSecurityWorkspace mode="universal" />
    </main>
  );
}
