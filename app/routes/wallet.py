from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.models import AppSetting
from app.services.ton_utils import validate_ton_address, normalize_address
from app.services.wallet_sync import sync_wallet
from app.extensions import db
from flask import current_app

wallet_bp = Blueprint("wallet", __name__)


@wallet_bp.route("/setup", methods=["GET", "POST"])
def setup():
    setting = AppSetting.get_active_wallet()
    if setting and setting.last_sync_at:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        address = request.form.get("wallet_address", "").strip()
        if not validate_ton_address(address):
            flash("Noto'g'ri TON hamyor manzili. Iltimos, EQ yoki UQ bilan boshlanadigan to'g'ri manzil kiriting.", "error")
            return render_template("wallet_setup.html")

        address = normalize_address(address)
        AppSetting.set_wallet(address)

        try:
            sync_wallet(address, current_app.config)
            flash("Hamyor muvaffaqiyatli ulandi va sinxronlashtirildi!", "success")
        except Exception as e:
            flash(f"Hamyor saqlandi, lekin sinxronlash muvaffaqiyatsiz bo'ldi: {str(e)}. Boshqaruv panelidan qayta urinib ko'ring.", "warning")

        return redirect(url_for("dashboard.index"))

    return render_template("wallet_setup.html")


@wallet_bp.route("/change-wallet", methods=["GET", "POST"])
def change_wallet():
    setting = AppSetting.get_active_wallet()

    if request.method == "POST":
        address = request.form.get("wallet_address", "").strip()
        confirm = request.form.get("confirm", "")

        if confirm != "yes":
            flash("Iltimos, hamyor o'zgartirishni tasdiqlang.", "error")
            return render_template("change_wallet.html", current_wallet=setting.wallet_address if setting else None)

        if not validate_ton_address(address):
            flash("Noto'g'ri TON hamyor manzili.", "error")
            return render_template("change_wallet.html", current_wallet=setting.wallet_address if setting else None)

        address = normalize_address(address)

        from app.models import Transaction, SyncLog
        if setting:
            Transaction.query.filter_by(wallet_address=setting.wallet_address).delete()
            SyncLog.query.filter_by(wallet_address=setting.wallet_address).delete()
            db.session.commit()

        AppSetting.set_wallet(address)

        try:
            sync_wallet(address, current_app.config)
            flash("Hamyor muvaffaqiyatli o'zgartirildi va sinxronlashtirildi!", "success")
        except Exception as e:
            flash(f"Yangi hamyor saqlandi, lekin sinxronlash muvaffaqiyatsiz bo'ldi: {str(e)}. Boshqaruv panelidan qayta urinib ko'ring.", "warning")

        return redirect(url_for("dashboard.index"))

    return render_template("change_wallet.html", current_wallet=setting.wallet_address if setting else None)
