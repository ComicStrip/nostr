# Flask page at /donate that creates a fresh NWC invoice and shows a QR
import io, base64, asyncio
from flask import Flask, request, render_template_string, abort
from nostr_sdk import NostrWalletConnectUri, Nwc, MakeInvoiceRequest, uniffi_set_event_loop
import qrcode

app = Flask(__name__)

# --- hardcoded NWC URI  ---
NWC_URI = "nostr+walletconnect://...@coinos.io"

DEFAULT_SATS  = 1000
DEFAULT_DESC  = "Donation via NWC"
DEFAULT_EXPIRY = 900  # seconds

HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Donate</title><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Inter,Arial,sans-serif;max-width:680px;margin:40px auto;padding:0 16px}
 .card{border:1px solid #e5e7eb;border-radius:16px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
 h1{margin:.2rem 0 1rem 0}.row{display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start}
 img{width:260px;height:260px}.mono{font-family:ui-monospace,Menlo,Consolas,monospace;word-break:break-all}
 label{font-size:.9rem;color:#374151}input,button{padding:10px 12px;border:1px solid #d1d5db;border-radius:10px}
 button{background:#fff;cursor:pointer}.muted{color:#6b7280;font-size:.9rem}

.btn{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  padding:10px 14px;
  min-width:150px;
  border:1px solid #d1d5db;
  border-radius:10px;
  background:#f7f7f7 !important;
  color:#111 !important;            /* force visible text */
  font-weight:600;
  font-size:.95rem;
  line-height:1;                     /* avoids clipping */
  white-space:nowrap;
  text-shadow:none;
  -webkit-appearance:none;           /* iOS Safari */
  appearance:none;
}
.btn::before, .btn::after{ content:none !important; } /* kill overlays */

</style></head><body>
<h1>Donate with Lightning (NWC)</h1>
<div class="card">
  <form method="GET" action="/donate" style="margin-bottom:16px">
    <label>Amount (sats): </label>
    <input type="number" name="amount" min="1" value="{{sats}}">


<button type="submit" class="btn">Create invoice</button>

  </form>
  <div class="row">
    <div><img alt="BOLT11 QR" src="data:image/png;base64,{{qr_b64}}"></div>
    <div style="flex:1;min-width:260px">
      <div class="muted">Description</div><div class="mono">{{desc}}</div>
      <div class="muted" style="margin-top:12px">BOLT11 invoice</div>
      <div class="mono" id="inv">{{invoice}}</div>
      <div style="margin-top:12px">
        <button onclick="navigator.clipboard.writeText(document.getElementById('inv').textContent)">Copy invoice</button>
      </div>
      <p class="muted" style="margin-top:16px">Expires in {{expiry}} seconds.</p>
    </div>
  </div>
</div></body></html>"""

async def _make_invoice(msats: int, desc: str, expiry: int) -> str:
    uniffi_set_event_loop(asyncio.get_running_loop())
    uri = NostrWalletConnectUri.parse(NWC_URI)
    nwc = Nwc(uri)
    params = MakeInvoiceRequest(amount=msats, description=desc, description_hash=None, expiry=expiry)
    res = await nwc.make_invoice(params)
    return res.invoice

def _qr_b64(text: str) -> str:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q)
    qr.add_data(text); qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

@app.route("/")
@app.route("/donate")
def donate():
    try:
        sats = int(request.args.get("amount", DEFAULT_SATS))
        if sats < 1: raise ValueError
    except ValueError:
        abort(400, "Invalid amount")
    invoice = asyncio.run(_make_invoice(sats * 1000, DEFAULT_DESC, DEFAULT_EXPIRY))
    return render_template_string(HTML,
        sats=sats, desc=DEFAULT_DESC, expiry=DEFAULT_EXPIRY,
        invoice=invoice, qr_b64=_qr_b64(invoice))

if __name__ == "__main__":
    # pip install flask nostr-sdk qrcode[pil]
    app.run(host="0.0.0.0", port=8000)
