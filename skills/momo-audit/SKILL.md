---
name: momo-audit
description: "Use when: momo, MoMo, thanh toan MoMo, signature, checksum, payWithMethod, loi giao dich MoMo. Huong dan phan tich tich hop MoMo va debug giao dich that bai."
---

# MoMo Audit Skill

## Muc tieu
- Tom tat luong tich hop MoMo trong he thong.
- Ra soat logic signature (HMAC SHA256).
- Kiem tra luong IPN va return.
- Dua ra checklist debug khi giao dich that bai.

## Cach su dung
Khi duoc goi, thuc hien nhanh cac buoc sau:

1) Xac dinh file trong codebase
- Tim cac file chinh lien quan MoMo.
- Uu tien: momo_utils.py, views.py, settings, frontend checkout.

2) Kiem tra cau hinh
- Doc MoMo config: partner_code, access_key, secret_key, endpoint, return_url, ipn_url.
- Dam bao URL return/ipn phu hop moi truong (local/sandbox/prod).

3) Kiem tra signature (HMAC SHA256)
- Signature format: `accessKey={key}&amount={amt}&extraData={extra}&ipnUrl={ipn}&orderId={id}&orderInfo={info}&partnerCode={code}&redirectUrl={redir}&requestId={req}&requestType=payWithMethod`
- **Quan trọng**: Dùng encoding `ascii` (không phải `utf-8`)
- **Quan trọng**: Dùng `requestType=payWithMethod` (không phải `payWithATM`)

4) Kiem tra callback signature verification
- Signature format: `accessKey={key}&amount={amt}&extraData={extra}&orderId={id}&orderInfo={info}&partnerCode={code}&requestId={req}`
- Không bao gồm redirectUrl, ipnUrl, orderType, partnerName, transId, message, responseTime, signature

5) Kiem tra momo_create
- Validate amount > 0.
- Tao order_id duy nhat.
- Build payment request va tra ve payUrl.

6) Kiem tra momo_return
- Chi verify signature khi co signature tu callback.
- Kiem tra resultCode == '0' la thanh cong.
- Cap nhat order status va gui thong bao Telegram.

7) Kiem tra momo_ipn
- Verify signature tu body request.
- Cap nhat order paid/failed.
- Tra response theo spec MoMo.

8) Checklist debug nhanh
- Secret key dung chua?
- Signature dung encoding (ascii) chua?
- requestType = 'payWithMethod' chua?
- Return URL va IPN URL co hop le, truy cap duoc?
- resultCode != 0 thi message gi?
- MoMo sandbox test MSISDN: 56733123453 (Success), 46733123450 (Failed)

## Output mong muon
- Danh sach file lien quan MoMo (link file).
- Nhan xet nhanh ve signature, return, ipn.
- Danh sach buoc debug uu tien (1-5 buoc).
