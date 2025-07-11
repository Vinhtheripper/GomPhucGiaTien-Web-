import ssl
from django.core.mail import EmailMessage
from django.utils.html import format_html
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import os
from django.conf import settings
from email.mime.image import MIMEImage
from django.core.mail import get_connection
from .models import ShippingAddress
from num2words import num2words

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Đăng ký font trước khi tạo Canvas
pdfmetrics.registerFont(TTFont('Roboto', os.path.join(settings.BASE_DIR, 'app/static/Roboto/static/Roboto-Regular.ttf')))

pdfmetrics.registerFont(TTFont('Roboto-Bold', os.path.join(settings.BASE_DIR, 'app/static/Roboto/static/Roboto-Bold.ttf')))

pdfmetrics.registerFont(TTFont('Roboto-ExtraBold', os.path.join(settings.BASE_DIR, 'app/static/Roboto/static/Roboto-ExtraBold.ttf')))

def truncate_text(text, max_length=30):
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def generate_invoice(order):
    """Tạo hóa đơn PDF chuyên nghiệp"""
    invoice_dir = os.path.join(settings.BASE_DIR, "invoices")
    os.makedirs(invoice_dir, exist_ok=True)
    pdf_path = os.path.join(invoice_dir, f"invoice_{order.id}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Roboto-Bold", 14)
    logo_path = os.path.join(settings.BASE_DIR, "app/static/app/images/logocrop.png")
    if os.path.exists(logo_path):
        c.drawImage(logo_path, 55, 710, width=55, height=55, mask='auto')

    c.setFillColor("#1d3557")
    c.drawCentredString(315, 750, "HÓA ĐƠN ĐIỆN TỬ / E-INVOICE")
    c.setFillColor(colors.black)
    c.setFont("Roboto", 12)
    c.drawString(120, 715, "Gốm Phúc Gia Tiên")
    c.drawString(120, 700, "669 Đỗ Mười, Khu phố 6, Thủ Đức, TP.HCM")
    c.drawString(120, 685, "Hotline: 0919 694 180 | Facebook: gomphucgiatien")
    c.setFont("Roboto-Bold", 12)
    c.drawString(420, 715, f"Mã đơn: {order.id}")
    c.drawString(420, 700, f"Ngày: {order.date_order.strftime('%d-%m-%Y')}")
    c.setFont("Roboto", 11)
    c.drawString(120, 660, f"Khách hàng: {order.customer.user.get_full_name() if order.customer else 'Ẩn danh'}")
    shipping_address = ShippingAddress.objects.filter(customer=order.customer).order_by('-date_added').first()
    c.drawString(120, 645, f"Địa chỉ nhận: {shipping_address.address if shipping_address else 'N/A'}")

    # Bảng sản phẩm
    data = [["STT", "Sản phẩm", "SL", "Đơn giá", "Thành tiền"]]
    for i, item in enumerate(order.orderitem_set.all()):
        if item.product:
            item_name = truncate_text(item.product.name, max_length=36)
            price = item.product.price
            data.append([
                i + 1,
                item_name,
                item.quantity,
                f"{int(price):,}₫",
                f"{int(item.get_total):,}₫"
            ])
    data.append(["", "Giảm giá", "", "", f"- {int(order.discount_amount):,}₫"])
    data.append(["", "Tổng cộng", "", "", f"{int(order.final_total):,}₫"])

    # Vẽ bảng
    table = Table(data, colWidths=[38, 200, 52, 85, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), "#48607c"),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Roboto-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
    ]))

    table.wrapOn(c, 120, 500)
    table_width = sum([38, 200, 52, 85, 100])
    table_x = (letter[0] - table_width) / 2
    table.drawOn(c, table_x, 500)

    c.setFont("Roboto-ExtraBold", 11)
    c.setFillColor("#1d3557")
    c.drawString(120, 475, f"Số tiền bằng chữ: {num2words(order.final_total, lang='vi').capitalize()} đồng")
    c.setFillColor(colors.black)

    c.drawString(130, 440, "Khách hàng")
    c.drawString(420, 440, "Đại diện cửa hàng")
    c.setFont("Roboto", 10)
    c.setFillColor("#a7a7a7")
    c.drawString(120, 405, "Cảm ơn bạn đã tin chọn Gốm Phúc Gia Tiên. Hẹn gặp lại bạn ở các đơn hàng tiếp theo!")
    c.save()
    return pdf_path



def send_invoice_email(customer_email, pdf_path, order):
    """Gửi email hóa đơn với logo, mẫu đẹp, lời cảm ơn chuyên nghiệp."""

    logo_path = os.path.join(settings.BASE_DIR, "app/static/app/images/logocrop.png")
    customer_name = order.customer.user.get_full_name() if order.customer else "Quý khách hàng"

    subject = f"🧾 [Gốm Phúc Gia Tiên] Đơn hàng #{order.id} của bạn đã được xác nhận!"
    message = format_html(
        """
        <div style="font-family: 'Segoe UI', Arial, sans-serif; border-radius:16px; border: 1px solid #e0e0e0; padding: 32px 24px; max-width: 540px; background: #fafaf9; margin:auto;">
            <img src="cid:delisora_logo" style="width:90px; height:auto; margin-bottom:12px;" alt="Gốm Phúc Gia Tiên"/>
            <h2 style="color: #19435f; margin-bottom:10px; font-size: 2em;">Cảm ơn bạn đã tin chọn Gốm Phúc Gia Tiên!</h2>
            <p style="font-size:1.13em; text-align: left;">
                Xin chào <b>{name}</b>,<br>
                Chúng tôi trân trọng thông báo đơn hàng <b>#{order_id}</b> của bạn đã được xác nhận.<br>
                Vui lòng xem hóa đơn chi tiết ở file đính kèm.<br>
            </p>
            <ul style="text-align:left; margin-left:1em;">
                <li>Ngày đặt: <b>{order_date}</b></li>
                <li>Giá trị đơn hàng: <b>{order_total:,.0f}₫</b></li>
                <li>Phương thức thanh toán: <b>{payment}</b></li>
            </ul>
            <p style="font-size:1.04em; color:#375c7d; text-align:left;">
                Đội ngũ Gốm Phúc Gia Tiên luôn mong muốn mang đến cho bạn những sản phẩm chất lượng &amp; trải nghiệm tốt nhất.<br>
                Nếu cần hỗ trợ, liên hệ Hotline <b>0919 694 180</b> hoặc trả lời email này.
            </p>
            <div style="color:#888; font-size:0.97em; margin-top:30px;">
                Trân trọng,<br>
                <b>Gốm Phúc Gia Tiên</b><br>
                669 Đỗ Mười, Khu phố 6, Thủ Đức, TP. HCM<br>
                Facebook: <a href="https://facebook.com/gomphucgiatien">facebook.com/gomphucgiatien</a>
            </div>
        </div>
        """.format(
            name=customer_name,
            order_id=order.id,
            order_date=order.date_order.strftime('%d/%m/%Y'),
            order_total=float(order.final_total),
            payment=order.get_payment_method_display()
        )
    )

    # Email connection như cũ
    connection = get_connection(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=True
    )
    connection.ssl_context.check_hostname = False
    connection.ssl_context.verify_mode = ssl.CERT_NONE

    email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [customer_email], connection=connection)
    email.content_subtype = "html"

    # Đính kèm logo nếu tồn tại
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img:
            logo = MIMEImage(img.read())
            logo.add_header("Content-ID", "<delisora_logo>")
            logo.add_header("Content-Disposition", "inline")
            logo.add_header("Content-Type", "image/png")
            email.attach(logo)

    # Đính kèm hóa đơn PDF nếu tồn tại
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as pdf:
            email.attach(f"invoice_{order.id}.pdf", pdf.read(), "application/pdf")

    email.send()



