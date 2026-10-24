"use client";
// Approval paths for the green half: a real platform passkey (Face ID / Touch ID / Windows Hello)
// via WebAuthn, or an Ed25519-signed vendor wallet rotation verified with WebCrypto.
import type { VendorWalletRotationRequest } from "./types";

const toHex = (b: ArrayBuffer) => Array.from(new Uint8Array(b), (x) => x.toString(16).padStart(2, "0")).join("");

const b64url = (b: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const fromB64url = (s: string) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));

/**
 * The 32 bytes of the kernel's settlement hash (hex). That hash commits to the green amount, recipient,
 * entitlement and a fresh nonce, so the signature approves exactly that payout, once.
 */
function intentChallenge(settlementHash: string): Uint8Array<ArrayBuffer> {
  const hex = settlementHash.replace(/^0x/, "");
  if (!/^[0-9a-fA-F]{64}$/.test(hex)) throw new Error("settlement hash must be 32 bytes of hex");
  const out = new Uint8Array(new ArrayBuffer(32));
  for (let i = 0; i < 32; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

const CRED_KEY = "heistbox:passkey-credential";

/** base64url of the 32 challenge bytes — exactly what WebAuthn writes into clientDataJSON.challenge. */
export const intentChallengeB64url = (intentHash: string) => b64url(intentChallenge(intentHash).buffer);

/** Drop the locally remembered passkey so the next tap registers a fresh one with the server. */
export const forgetStoredPasskey = () => {
  try {
    localStorage.removeItem(CRED_KEY);
  } catch {}
};

export const hasStoredPasskey = () => {
  try {
    return Boolean(localStorage.getItem(CRED_KEY));
  } catch {
    return false;
  }
};

export interface PasskeyOutcome {
  ok: boolean;
  mode: "webauthn-create" | "webauthn-get" | "unavailable" | "cancelled";
  ms: number;
  error?: string;
  credential_id?: string;
  assertion?: Record<string, string>;
  /** Signature over authenticatorData‖SHA-256(clientDataJSON), checked here with WebCrypto against the stored public key. */
  browser_signature_valid?: boolean | null;
  browser_check_note?: string;
}

/** ES256 signatures from authenticators are ASN.1 DER; WebCrypto wants raw r‖s (64 bytes). */
function derToRaw(der: Uint8Array): Uint8Array<ArrayBuffer> {
  const out = new Uint8Array(new ArrayBuffer(64));
  let i = 2;
  if (der[1] & 0x80) i += der[1] & 0x7f;
  const readInt = (dst: number) => {
    if (der[i] !== 0x02) throw new Error("bad DER");
    const len = der[i + 1];
    let v = der.slice(i + 2, i + 2 + len);
    i += 2 + len;
    while (v.length > 32 && v[0] === 0) v = v.slice(1);
    out.set(v, dst + 32 - v.length);
  };
  readInt(0);
  readInt(32);
  return out;
}

async function verifyAssertionSignature(
  spkiB64: string,
  alg: number,
  authData: ArrayBuffer,
  clientDataJSON: ArrayBuffer,
  signature: ArrayBuffer,
): Promise<{ valid: boolean | null; note: string }> {
  if (!crypto?.subtle) return { valid: null, note: "SubtleCrypto unavailable on this origin" };
  try {
    const spki = fromB64url(spkiB64);
    const cdHash = new Uint8Array(await crypto.subtle.digest("SHA-256", clientDataJSON));
    const ad = new Uint8Array(authData);
    const signed = new Uint8Array(new ArrayBuffer(ad.length + cdHash.length));
    signed.set(ad, 0);
    signed.set(cdHash, ad.length);
    if (alg === -7) {
      const key = await crypto.subtle.importKey("spki", spki, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
      const valid = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, key, derToRaw(new Uint8Array(signature)), signed);
      return { valid, note: "ES256 (P-256) checked in-browser with WebCrypto" };
    }
    if (alg === -257) {
      const key = await crypto.subtle.importKey("spki", spki, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
      const valid = await crypto.subtle.verify({ name: "RSASSA-PKCS1-v1_5" }, key, new Uint8Array(signature), signed);
      return { valid, note: "RS256 checked in-browser with WebCrypto" };
    }
    return { valid: null, note: `unsupported COSE alg ${alg}` };
  } catch (e) {
    return { valid: null, note: `could not check signature: ${e instanceof Error ? e.message : String(e)}` };
  }
}

/**
 * Real WebAuthn with the platform authenticator (Face ID / Touch ID / Windows Hello).
 * First use registers a passkey for this origin (navigator.credentials.create); later taps sign the
 * intent challenge with it (navigator.credentials.get). Never reports success unless the authenticator did.
 */
export async function approveWithPasskey(settlementHash: string): Promise<PasskeyOutcome> {
  const t0 = performance.now();
  if (typeof window === "undefined" || !window.PublicKeyCredential || !navigator.credentials) {
    return { ok: false, mode: "unavailable", ms: 0, error: "WebAuthn is not available in this browser/context (needs HTTPS or localhost)." };
  }
  let challenge: Uint8Array<ArrayBuffer>;
  try {
    challenge = intentChallenge(settlementHash);
  } catch (e) {
    return { ok: false, mode: "unavailable", ms: 0, error: e instanceof Error ? e.message : String(e) };
  }
  let stored: { id: string; publicKey: string | null; alg?: number } | null = null;
  try {
    const raw = localStorage.getItem(CRED_KEY);
    stored = raw ? (JSON.parse(raw) as { id: string; publicKey: string | null; alg?: number }) : null;
  } catch {}

  try {
    if (stored) {
      const cred = (await navigator.credentials.get({
        publicKey: { challenge, allowCredentials: [{ type: "public-key", id: fromB64url(stored.id) }], userVerification: "required", timeout: 60000 },
      })) as PublicKeyCredential | null;
      if (!cred) return { ok: false, mode: "cancelled", ms: performance.now() - t0 };
      const r = cred.response as AuthenticatorAssertionResponse;
      const ms = performance.now() - t0;
      const check = stored.publicKey
        ? await verifyAssertionSignature(stored.publicKey, stored.alg ?? -7, r.authenticatorData, r.clientDataJSON, r.signature)
        : { valid: null, note: "no public key was exported at registration, so the signature can't be checked here" };
      return {
        ok: true,
        mode: "webauthn-get",
        ms,
        credential_id: stored.id,
        browser_signature_valid: check.valid,
        browser_check_note: check.note,
        assertion: {
          client_data_json: new TextDecoder().decode(r.clientDataJSON),
          client_data_b64: b64url(r.clientDataJSON),
          authenticator_data: b64url(r.authenticatorData),
          signature: b64url(r.signature),
          ...(r.userHandle ? { user_handle: b64url(r.userHandle) } : {}),
        },
      };
    }
    const cred = (await navigator.credentials.create({
      publicKey: {
        challenge,
        rp: { name: "HeistBox Enclave" },
        user: { id: crypto.getRandomValues(new Uint8Array(16)), name: "cfo@heistbox", displayName: "HeistBox CFO" },
        pubKeyCredParams: [
          { type: "public-key", alg: -7 },
          { type: "public-key", alg: -257 },
        ],
        authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required", residentKey: "preferred" },
        timeout: 60000,
      },
    })) as PublicKeyCredential | null;
    if (!cred) return { ok: false, mode: "cancelled", ms: performance.now() - t0 };
    const r = cred.response as AuthenticatorAttestationResponse;
    const pk = typeof r.getPublicKey === "function" ? r.getPublicKey() : null;
    const alg = typeof r.getPublicKeyAlgorithm === "function" ? r.getPublicKeyAlgorithm() : -7;
    const id = b64url(cred.rawId);
    try {
      localStorage.setItem(CRED_KEY, JSON.stringify({ id, publicKey: pk ? b64url(pk) : null, alg }));
    } catch {}
    return {
      ok: true,
      mode: "webauthn-create",
      ms: performance.now() - t0,
      credential_id: id,
      assertion: {
        client_data_json: new TextDecoder().decode(r.clientDataJSON),
        client_data_b64: b64url(r.clientDataJSON),
        attestation_object: b64url(r.attestationObject),
        ...(pk ? { credential_public_key: b64url(pk) } : {}),
      },
    };
  } catch (e) {
    const name = e instanceof DOMException ? e.name : "";
    // A stale stored credential (deleted from the device) — forget it so the next tap re-registers.
    if (stored && (name === "NotAllowedError" || name === "InvalidStateError")) {
      try {
        localStorage.removeItem(CRED_KEY);
      } catch {}
    }
    return { ok: false, mode: name === "NotAllowedError" ? "cancelled" : "unavailable", ms: performance.now() - t0, error: e instanceof Error ? e.message : String(e) };
  }
}

export interface SignedRotation {
  body: VendorWalletRotationRequest;
  verified: boolean;
  verify_us: number;
  mode: "webcrypto-ed25519" | "unsupported";
}

export async function signAndVerifyRotation(opts: { work_item_id: string; old_wallet: string; new_wallet: string }): Promise<SignedRotation> {
  const nonce = toHex(crypto.getRandomValues(new Uint8Array(16)).buffer);
  const vendor_id = "vendor_acme_01";
  // Must match kernel/db_gate.py vendor_rotate_wallet: f"{vendor_id}:{work_item_id}:{old}:{new}:{nonce}"
  const msg = new TextEncoder().encode(`${vendor_id}:${opts.work_item_id}:${opts.old_wallet}:${opts.new_wallet}:${nonce}`);
  const base = { vendor_id, work_item_id: opts.work_item_id, old_wallet: opts.old_wallet, new_wallet: opts.new_wallet, nonce };
  try {
    const kp = (await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"])) as CryptoKeyPair;
    const sig = await crypto.subtle.sign({ name: "Ed25519" }, kp.privateKey, msg);
    const pub = await crypto.subtle.exportKey("raw", kp.publicKey);
    const t0 = performance.now();
    const ok = await crypto.subtle.verify({ name: "Ed25519" }, kp.publicKey, sig, msg);
    const us = Math.max(1, Math.round((performance.now() - t0) * 1000));
    return { body: { ...base, public_key_hex: toHex(pub), signature_hex: toHex(sig) }, verified: ok, verify_us: us, mode: "webcrypto-ed25519" };
  } catch {
    // No Ed25519 in this browser's WebCrypto: send nothing signed and let the kernel reject it.
    return { body: { ...base, public_key_hex: "", signature_hex: "" }, verified: false, verify_us: 0, mode: "unsupported" };
  }
}
