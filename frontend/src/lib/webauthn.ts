export function isWebAuthnSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.PublicKeyCredential !== "undefined" &&
    typeof navigator !== "undefined" &&
    Boolean(navigator.credentials?.create) &&
    Boolean(navigator.credentials?.get)
  );
}

export function base64urlToBuffer(b64u: string): ArrayBuffer {
  const padded = b64u.replace(/-/g, "+").replace(/_/g, "/");
  const padLen = (4 - (padded.length % 4)) % 4;
  const bin = atob(padded + "=".repeat(padLen));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) {
    bytes[i] = bin.charCodeAt(i);
  }
  return bytes.buffer;
}

export function bufferToBase64url(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 1) {
    bin += String.fromCharCode(bytes[i]);
  }
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function normalizeWebAuthnError(err: unknown): Error {
  if (err && typeof err === "object" && "name" in err && (err as { name: string }).name === "NotAllowedError") {
    return new Error("WEBAUTHN_CANCELLED");
  }
  return err instanceof Error ? err : new Error("PASSKEY_VERIFICATION_FAILED");
}

type JsonDescriptor = {
  id: string;
  type: PublicKeyCredentialType;
  transports?: AuthenticatorTransport[];
};

export async function createPasskeyCredential(publicKeyJson: Record<string, unknown>): Promise<Record<string, unknown>> {
  if (!isWebAuthnSupported()) {
    throw new Error("WEBAUTHN_UNSUPPORTED");
  }

  const userObj = (publicKeyJson.user || {}) as Record<string, unknown>;
  const excludeList = Array.isArray(publicKeyJson.excludeCredentials)
    ? (publicKeyJson.excludeCredentials as JsonDescriptor[])
    : [];

  const creationOptions: PublicKeyCredentialCreationOptions = {
    ...(publicKeyJson as unknown as PublicKeyCredentialCreationOptions),
    challenge: base64urlToBuffer(String(publicKeyJson.challenge || "")),
    user: {
      ...(userObj as unknown as PublicKeyCredentialUserEntity),
      id: base64urlToBuffer(String(userObj.id || "")),
    },
    excludeCredentials: excludeList.map((item) => ({
      ...item,
      id: base64urlToBuffer(String(item.id)),
    })),
  };

  let created: Credential | null;
  try {
    created = await navigator.credentials.create({ publicKey: creationOptions });
  } catch (err: unknown) {
    throw normalizeWebAuthnError(err);
  }
  if (!created || !(created instanceof PublicKeyCredential) || !created.response) {
    throw new Error("PASSKEY_VERIFICATION_FAILED");
  }

  const att = created.response as AuthenticatorAttestationResponse;
  return {
    id: created.id,
    rawId: bufferToBase64url(created.rawId),
    type: created.type,
    response: {
      clientDataJSON: bufferToBase64url(att.clientDataJSON),
      attestationObject: bufferToBase64url(att.attestationObject),
      transports: typeof att.getTransports === "function" ? att.getTransports() : [],
    },
    clientExtensionResults:
      typeof created.getClientExtensionResults === "function" ? created.getClientExtensionResults() : {},
  };
}

export async function getPasskeyAssertion(publicKeyJson: Record<string, unknown>): Promise<Record<string, unknown>> {
  if (!isWebAuthnSupported()) {
    throw new Error("WEBAUTHN_UNSUPPORTED");
  }

  const allowList = Array.isArray(publicKeyJson.allowCredentials)
    ? (publicKeyJson.allowCredentials as JsonDescriptor[])
    : [];

  const requestOptions: PublicKeyCredentialRequestOptions = {
    ...(publicKeyJson as unknown as PublicKeyCredentialRequestOptions),
    challenge: base64urlToBuffer(String(publicKeyJson.challenge || "")),
    allowCredentials: allowList.map((item) => ({
      ...item,
      id: base64urlToBuffer(String(item.id)),
    })),
  };

  let assertion: Credential | null;
  try {
    assertion = await navigator.credentials.get({ publicKey: requestOptions });
  } catch (err: unknown) {
    throw normalizeWebAuthnError(err);
  }
  if (!assertion || !(assertion instanceof PublicKeyCredential) || !assertion.response) {
    throw new Error("PASSKEY_VERIFICATION_FAILED");
  }

  const res = assertion.response as AuthenticatorAssertionResponse;
  return {
    id: assertion.id,
    rawId: bufferToBase64url(assertion.rawId),
    type: assertion.type,
    response: {
      clientDataJSON: bufferToBase64url(res.clientDataJSON),
      authenticatorData: bufferToBase64url(res.authenticatorData),
      signature: bufferToBase64url(res.signature),
      userHandle: res.userHandle ? bufferToBase64url(res.userHandle) : null,
    },
    clientExtensionResults:
      typeof assertion.getClientExtensionResults === "function" ? assertion.getClientExtensionResults() : {},
  };
}
