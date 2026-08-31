# Task 007: LAN Access, HTTPS & Network Security System

## Goal
Enable secure HTTPS LAN access across devices, automated self-signed SSL certificates, and firewall rule creation.

## Requirements
- Automated OpenSSL certificate generation (`cert.pem`, `key.pem`)
- SAN support (Subject Alternative Names for localhost, hostname, `.local` mDNS, and LAN IPs)
- Built-in certificate download endpoint (`GET /download-cert`)
- Windows Firewall inbound rule automation (Port 8000)
- Multi-address startup access banner
- `SYSTEM_PASSWORD` authentication for administrative actions

## Acceptance
- Application is securely accessible over HTTPS from mobile phones and PCs on the local network.

---

## 💎 Completion & Verification Status

### Status: COMPLETED

1. **Automated HTTPS Provisioning**: Startup scripts generate self-signed SSL certificates with SAN support.
2. **SSL Certificate Distribution**: Built `/download-cert` route returning `assetvault_cert.crt`.
3. **Firewall Automation**: Automated creation of Windows Firewall rule `"AssetVault - Port 8000"`.
4. **Access Banner**: Console banner prints Local, Hostname, mDNS (`.local`), and Network IP URLs.
5. **System Password Protection**: Protected storage migration and database purge actions with `SYSTEM_PASSWORD`.

### Verification Metrics
- Server boots with HTTPS enabled on port 8000 and answers LAN requests.
