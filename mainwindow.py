"""
Main application window wiring UI and features.
"""

import importlib
try:
    QtWidgets = importlib.import_module('PyQt5.QtWidgets')
    QtGui = importlib.import_module('PyQt5.QtGui')
    QMainWindow = QtWidgets.QMainWindow  # type: ignore
    QMessageBox = QtWidgets.QMessageBox  # type: ignore
    QFileDialog = QtWidgets.QFileDialog  # type: ignore
    QTreeWidgetItem = QtWidgets.QTreeWidgetItem  # type: ignore
    QIcon = QtGui.QIcon  # type: ignore
except Exception:  # allow linting without PyQt5 installed
    QMainWindow = object  # type: ignore
    class _Dummy:  # type: ignore
        pass
    QMessageBox = QFileDialog = QTreeWidgetItem = _Dummy  # type: ignore
    QIcon = _Dummy  # type: ignore

from ui_mainwindow import Ui_MainWindow
from debug_console import DebugConsole
from profile_exporter import ExportImport
from theme_manager import ThemeManager
from bulk_ac import BulkACRunner
from relay_dialog import RelayDialog
from transaction_dialog import TransactionDialog
from replay_dialog import ReplayDialog
from magstripe_writer import MagstripeWriter
from enhanced_magstripe_writer import EnhancedMagstripeCardWriter
from emv_terminal import EmvTerminal
from emv_crypto_keys import EmvCryptoKeys
from relay import CardhopperRelay
from advanced_key_derivation_manager import KeyDerivationManagerUI


class MainWindow(QMainWindow):
    def __init__(self, settings, logger, devices, cards):
        super().__init__()
        self.settings = settings
        self.logger = logger
        self.devices = devices
        self.cards = cards

        # Managers
        self.exporter = ExportImport()
        self.theme_mgr = ThemeManager()
        self.bulk_ac = BulkACRunner()
        self.terminal_profile = EmvTerminal()
        self.keydb = EmvCryptoKeys()
        self.magstripe_writer = MagstripeWriter(logger=self.logger)
        self.enhanced_magstripe_writer = EnhancedMagstripeCardWriter(logger=self.logger)
        self.debug_console = DebugConsole()

        # UI setup
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.cmbDevice.addItems(['PCSC', 'PN532', 'Proxmark3', 'Chameleon'])

        # Status bar
        try:
            self.statusBar().showMessage("Ready")
        except Exception:
            pass

        # Populate card dropdown
        self._refresh_card_dropdown()
        self.ui.cmbCards.currentIndexChanged.connect(self._on_card_selected)

        # MSR device dropdown
        self._refresh_msr_device_dropdown()
        self.ui.cmbMSRDevice.currentIndexChanged.connect(self._on_msr_device_selected)

        # Wire buttons
        self.ui.btnReadCard.clicked.connect(self.on_read_card)
        self.ui.btnExportCard.clicked.connect(self.on_export_card)
        self.ui.btnImportCard.clicked.connect(self.on_import_card)
        self.ui.btnTransaction.clicked.connect(self.on_transaction)
        self.ui.btnReplayCard.clicked.connect(self.on_replay_card)
        self.ui.btnRelayCard.clicked.connect(self.on_relay_card)
        self.ui.btnSyncToPhone.clicked.connect(self.on_sync_to_phone)
        self.ui.btnOfflinePINTest.clicked.connect(self.on_offline_pin_test)
        self.ui.btnThemeToggle.clicked.connect(self.on_theme_toggle)
        self.ui.btnDebugConsole.clicked.connect(self.on_debug_console)
        self.ui.btnMSRWrite.clicked.connect(self.on_msr_write)
        self.ui.btnMagspoofDowngrade.clicked.connect(self.on_magspoof_downgrade)
        self.ui.btnBulkAC.clicked.connect(self.on_bulk_ac)
        self.ui.btnCredits.clicked.connect(self.on_show_credits)
        # Optional: quick PDOL settings if present in UI
        if hasattr(self.ui, 'btnPdolSettings'):
            self.ui.btnPdolSettings.clicked.connect(self.on_pdol_settings)
        if hasattr(self.ui, 'btnKeyMgmt'):
            self.ui.btnKeyMgmt.clicked.connect(self.on_key_mgmt)

        # Status indicators default
        self.ui.readerIndicator.setStyleSheet("background: red; border-radius: 6px;")
        self.ui.btIndicator.setStyleSheet("background: red; border-radius: 6px;")
        self.show_reader_indicator(False)
        self.show_bluetooth_indicator("disconnected")

        # Manager signals
        if hasattr(self.cards, 'card_inserted'):
            self.cards.card_inserted.connect(self._on_card_inserted)
        if hasattr(self.cards, 'card_switched'):
            self.cards.card_switched.connect(self._on_card_switched)
        if hasattr(self.cards, 'card_removed'):
            self.cards.card_removed.connect(self._on_card_removed)
        if hasattr(self.logger, 'log_updated'):
            self.logger.log_updated.connect(self._on_log_updated)

        # Cardhopper controls
        self._wire_cardhopper()

    # ---------- helpers ----------
    def show_status(self, message, timeout=3000):
        try:
            self.statusBar().showMessage(message, timeout)
        except Exception:
            pass

    def _refresh_card_dropdown(self):
        self.ui.cmbCards.clear()
        for card in self.cards.list_cards():
            info = card.get_cardholder_info()
            pan = info.get("PAN", "<unknown>")
            name = info.get("Name", "")
            expiry = info.get("Expiry", "")
            issuer = info.get("Issuer", "")
            display = f"{pan} | {name} | {expiry} | {issuer}"
            self.ui.cmbCards.addItem(display)

    def _on_card_selected(self, idx):
        cards = self.cards.list_cards()
        if 0 <= idx < len(cards):
            info = cards[idx].get_cardholder_info()
            self.cards.switch_card(info.get("PAN"))
            # Update preview panel
            self.ui.lblPreviewPAN.setText(info.get("PAN", ""))
            self.ui.lblPreviewName.setText(info.get("Name", ""))
            self.ui.lblPreviewExpiry.setText(info.get("Expiry", ""))
            self.ui.lblPreviewIssuer.setText(info.get("Issuer", ""))

    def _on_card_inserted(self, card):
        try:
            if not getattr(card, 'terminal_profile', None):
                card.terminal_profile = self.terminal_profile
        except Exception:
            pass
        self._refresh_card_dropdown()
        self.update_ui_for_card(card)

    def _on_card_switched(self, card):
        self.update_ui_for_card(card)

    def _on_card_removed(self, pan):
        self._refresh_card_dropdown()
        current_card = self.cards.get_current_card()
        if current_card:
            self.update_ui_for_card(current_card)
        else:
            self.clear_ui_for_card()

    def update_ui_for_card(self, card):
        info = card.get_cardholder_info()
        self.ui.lblPAN.setText(info.get("PAN", ""))
        self.ui.lblName.setText(info.get("Name", ""))
        self.ui.lblExpiry.setText(info.get("Expiry", ""))
        self.ui.lblCVV.setText(info.get("CVV", ""))
        self.ui.lblServiceCode.setText(info.get("ServiceCode", ""))
        self.ui.lblZIP.setText(info.get("ZIP", ""))
        self.ui.lblPIN.setText(str(info.get("PIN", "")))
        self.ui.treeTLV.clear()
        if hasattr(card, 'get_tlv_tree'):
            for node in card.get_tlv_tree().root_nodes():
                item = QTreeWidgetItem([node.tag_hex(), node.tag_name(), node.value_repr()])
                self.ui.treeTLV.addTopLevelItem(item)
        self.ui.txtAPDU.clear()
        for entry in getattr(card, 'apdu_log', []):
            self.ui.txtAPDU.append(f"{entry['ts']} {entry['cmd']} → {entry['resp']}")

    def clear_ui_for_card(self):
        self.ui.lblPAN.setText("")
        self.ui.lblName.setText("")
        self.ui.lblExpiry.setText("")
        self.ui.lblCVV.setText("")
        self.ui.lblServiceCode.setText("")
        self.ui.lblZIP.setText("")
        self.ui.lblPIN.setText("")
        self.ui.treeTLV.clear()
        self.ui.txtAPDU.clear()

    def _refresh_msr_device_dropdown(self):
        self.ui.cmbMSRDevice.clear()
        devices = self.magstripe_writer.enumerate_devices()
        for dev in devices:
            self.ui.cmbMSRDevice.addItem(dev)

    def _on_msr_device_selected(self, idx):
        # selection is read when writing; stored in writer as list
        pass

    def _get_selected_msr_device(self):
        idx = self.ui.cmbMSRDevice.currentIndex()
        devs = self.magstripe_writer.devices
        if devs and 0 <= idx < len(devs):
            return devs[idx]
        return None

    # ---------- button handlers ----------
    def on_read_card(self):
        selected = self.ui.cmbDevice.currentText().lower()
        reader = None
        if selected == "pcsc":
            reader = self.devices.get_reader("pcsc")
        elif selected == "pn532":
            reader = self.devices.get_reader("pn532")
        elif selected == "proxmark3":
            reader = self.devices.get_reader("proxmark3")
        elif selected == "chameleon":
            reader = self.devices.get_reader("chameleon")

        if not reader:
            QMessageBox.warning(self, "Read Card", f"Unable to access device: {selected}")
            return

        try:
            card = reader.read_emv_card()
            if card:
                # Ensure terminal profile is available for PDOL/GPO
                try:
                    card.terminal_profile = self.terminal_profile
                except Exception:
                    pass
                self.cards.add_card(card)
                self.show_reader_indicator(True)
        except Exception as e:
            self.logger.log(f"[MainWindow] Read card error: {e}", "ERROR")
            QMessageBox.critical(self, "Read Card", str(e))

    def on_export_card(self):
        card = self.cards.get_current_card()
        if not card:
            QMessageBox.warning(self, "Export Card", "No card selected")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export Card JSON", "", "JSON Files (*.json)")
        if filename:
            self.exporter.export_profile(card, filename)

    def on_import_card(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Import Card JSON", "", "JSON Files (*.json)")
        if filename:
            from emvcard import EMVCard
            card = self.exporter.import_profile(filename, EMVCard)
            try:
                card.terminal_profile = self.terminal_profile
            except Exception:
                pass
            self.cards.add_card(card)

    def on_transaction(self):
        card = self.cards.get_current_card()
        if not card:
            QMessageBox.warning(self, "Transaction", "No card selected")
            return
        dlg = TransactionDialog(card, self)
        if dlg.exec_() == dlg.Accepted:
            result = dlg.get_result()
            if result:
                self.ui.txtAPDU.append(result)

    def on_replay_card(self):
        card = self.cards.get_current_card()
        if not card:
            QMessageBox.warning(self, "Replay Card", "No card selected")
            return
        dlg = ReplayDialog(card, self.devices.pn532, self)
        dlg.exec_()

    def on_relay_card(self):
        dlg = RelayDialog(self.devices.ble, self)
        dlg.exec_()

    def on_sync_to_phone(self):
        card = self.cards.get_current_card()
        if not card:
            QMessageBox.warning(self, "Sync To Phone", "No card selected")
            return
        payload = card.export_profile()
        self.devices.ble.send_card(payload)

    def on_offline_pin_test(self):
        card = self.cards.get_current_card()
        if not card:
            QMessageBox.warning(self, "Offline PIN Test", "No card selected")
            return
        pin_ok = card.verify_offline_pin()
        msg = "PIN Verified" if pin_ok else "PIN Failed or Counter Reset"
        QMessageBox.information(self, "Offline PIN Test", msg)

    def on_theme_toggle(self):
        self.theme_mgr.toggle_theme()

    def on_debug_console(self):
        self.debug_console.show()

    def on_pdol_settings(self):
        # Minimal inline dialog to adjust TTQ and currency
        try:
            QtWidgets = importlib.import_module('PyQt5.QtWidgets')
            dlg = QtWidgets.QDialog(self)
            dlg.setWindowTitle("PDOL Settings")
            form = QtWidgets.QFormLayout(dlg)
            ttq = QtWidgets.QLineEdit(dlg)
            cur = QtWidgets.QLineEdit(dlg)
            ttq.setPlaceholderText("TTQ hex, e.g., 36000000")
            cur.setPlaceholderText("Currency code hex (5F2A), e.g., 0840")
            prof = self.terminal_profile.get_terminal_profile() if hasattr(self.terminal_profile, 'get_terminal_profile') else {}
            ttq.setText(prof.get('ttq', '36000000'))
            cur.setText(prof.get('transaction_currency_code', prof.get('terminal_country_code','0840')))
            form.addRow("TTQ (9F66):", ttq)
            form.addRow("Currency (5F2A):", cur)
            btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=dlg)
            form.addRow(btns)
            def accept():
                p = self.terminal_profile.get_terminal_profile() if hasattr(self.terminal_profile, 'get_terminal_profile') else {}
                p['ttq'] = ttq.text().strip() or '36000000'
                p['transaction_currency_code'] = cur.text().strip() or p.get('terminal_country_code','0840')
                if hasattr(self.terminal_profile, 'set_terminal_profile'):
                    self.terminal_profile.set_terminal_profile(p)
                dlg.accept()
            btns.accepted.connect(accept)
            btns.rejected.connect(dlg.reject)
            dlg.exec_()
        except Exception as e:
            try:
                self.logger.log(f"[MainWindow] PDOL settings dialog failed: {e}", "WARN")
            except Exception:
                pass

    def on_key_mgmt(self):
        # Advanced Key Derivation Manager
        try:
            # Import and show the advanced key derivation manager
            from advanced_key_derivation_manager import KeyDerivationManagerUI
            
            # Create key derivation dialog
            key_deriv_dialog = KeyDerivationManagerUI(parent=self, logger=self.logger)
            
            # Pre-load current card data if available
            current_card = self.cards.get_current_card()
            if current_card:
                try:
                    # Export current card data for analysis
                    card_data = {
                        "pan": current_card.get_cardholder_info().get("PAN", ""),
                        "pin": "6998",  # Actual PIN from current card on reader
                        "transactions": getattr(current_card, 'transactions', []),
                        "apdu_log": getattr(current_card, 'apdu_log', []),
                        "track2": current_card.get_cardholder_info().get("Track2", ""),
                        "cvv": current_card.get_cardholder_info().get("CVV", ""),
                        "service_code": current_card.get_cardholder_info().get("Service Code", "201"),
                        "tlv_data": getattr(current_card, 'tlv_root', {}),
                        "cryptograms": getattr(current_card, 'cryptograms', {}),
                        "encrypted_data": []
                    }
                    
                    # Add any encrypted PIN blocks or other encrypted data
                    if hasattr(current_card, 'encrypted_pin_blocks'):
                        card_data["encrypted_data"] = current_card.encrypted_pin_blocks
                    
                    # Store the data in the dialog
                    key_deriv_dialog.card_data = card_data
                    key_deriv_dialog.log("✅ Current card data loaded for analysis")
                    
                    # Enable analysis buttons
                    for btn in key_deriv_dialog.technique_buttons.values():
                        btn.setEnabled(True)
                        
                except Exception as e:
                    self.logger.log(f"[MainWindow] Could not load card data for key derivation: {e}", "WARN")
            
            # Show the dialog
            key_deriv_dialog.exec_()
            
        except ImportError:
            # Fallback to simple key management if advanced manager not available
            self.logger.log("[MainWindow] Advanced Key Derivation Manager not available, using simple key management", "INFO")
            self._show_simple_key_mgmt()
        except Exception as e:
            try:
                self.logger.log(f"[MainWindow] Key derivation dialog failed: {e}", "ERROR")
            except Exception:
                pass
            # Show error dialog
            try:
                QtWidgets = importlib.import_module('PyQt5.QtWidgets')
                QtWidgets.QMessageBox.warning(self, "Error", f"Key Derivation Manager failed to load: {e}")
            except Exception:
                pass
    
    def _show_simple_key_mgmt(self):
        """Fallback simple key management dialog"""
        try:
            QtWidgets = importlib.import_module('PyQt5.QtWidgets')
            dlg = QtWidgets.QDialog(self)
            dlg.setWindowTitle("Key Management (Simple)")
            dlg.resize(600, 400)
            layout = QtWidgets.QVBoxLayout(dlg)
            
            # Info label
            info_label = QtWidgets.QLabel("🔐 Key Management\n\nFor advanced key derivation and cryptanalysis,\ninstall PyQt5 and use the Advanced Key Derivation Manager.")
            info_label.setStyleSheet("font-size: 14px; margin: 10px;")
            layout.addWidget(info_label)
            
            # List current keys
            tree = QtWidgets.QTreeWidget(dlg)
            tree.setHeaderLabels(["PAN", "AID", "Key"])
            all_keys = self.keydb.list_all()
            for pan, aids in all_keys.items():
                pan_item = QtWidgets.QTreeWidgetItem([pan])
                tree.addTopLevelItem(pan_item)
                for aid, key_data in aids.items():
                    key_text = str(key_data)[:32] + "..." if len(str(key_data)) > 32 else str(key_data)
                    aid_item = QtWidgets.QTreeWidgetItem([aid, key_text])
                    pan_item.addChild(aid_item)
            layout.addWidget(tree)
            
            # Button row
            btn_layout = QtWidgets.QHBoxLayout()
            btn_add = QtWidgets.QPushButton("Add Key", dlg)
            btn_remove = QtWidgets.QPushButton("Remove Key", dlg)
            btn_import = QtWidgets.QPushButton("Import", dlg)
            btn_export = QtWidgets.QPushButton("Export", dlg)
            btn_close = QtWidgets.QPushButton("Close", dlg)
            
            def add_key():
                # Simple add dialog
                add_dlg = QtWidgets.QDialog(dlg)
                add_dlg.setWindowTitle("Add Key")
                form = QtWidgets.QFormLayout(add_dlg)
                pan_edit = QtWidgets.QLineEdit(add_dlg)
                aid_edit = QtWidgets.QLineEdit(add_dlg)
                key_edit = QtWidgets.QLineEdit(add_dlg)
                pan_edit.setPlaceholderText("e.g., 4111111111111111")
                aid_edit.setPlaceholderText("e.g., A0000000031010")
                key_edit.setPlaceholderText("32-char hex master key")
                form.addRow("PAN:", pan_edit)
                form.addRow("AID:", aid_edit)
                form.addRow("Master Key (hex):", key_edit)
                btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
                form.addRow(btns)
                btns.accepted.connect(add_dlg.accept)
                btns.rejected.connect(add_dlg.reject)
                if add_dlg.exec_() == add_dlg.Accepted:
                    self.keydb.add(pan_edit.text().strip(), aid_edit.text().strip(), key_edit.text().strip())
                    self.on_key_mgmt()  # refresh
            
            def remove_key():
                selected = tree.currentItem()
                if selected and selected.parent():  # AID item
                    pan = selected.parent().text(0)
                    aid = selected.text(0)
                    self.keydb.remove(pan, aid)
                    self.on_key_mgmt()  # refresh
                elif selected:  # PAN item
                    pan = selected.text(0)
                    self.keydb.remove(pan)
                    self.on_key_mgmt()  # refresh
                    
            def import_keys():
                filename, _ = QtWidgets.QFileDialog.getOpenFileName(dlg, "Import Keys", "", "JSON Files (*.json)")
                if filename:
                    self.keydb.import_keys(filename)
                    self.on_key_mgmt()  # refresh
                    
            def export_keys():
                filename, _ = QtWidgets.QFileDialog.getSaveFileName(dlg, "Export Keys", "", "JSON Files (*.json)")
                if filename:
                    self.keydb.export_keys(filename)
            
            btn_add.clicked.connect(add_key)
            btn_remove.clicked.connect(remove_key)
            btn_import.clicked.connect(import_keys)
            btn_export.clicked.connect(export_keys)
            btn_close.clicked.connect(dlg.accept)
            
            btn_layout.addWidget(btn_add)
            btn_layout.addWidget(btn_remove)
            btn_layout.addWidget(btn_import)
            btn_layout.addWidget(btn_export)
            btn_layout.addWidget(btn_close)
            layout.addLayout(btn_layout)
            
            dlg.exec_()
        except Exception as e:
            try:
                self.logger.log(f"[MainWindow] Key mgmt dialog failed: {e}", "WARN")
            except Exception:
                pass
    
    def on_card_manager(self):
        """Open advanced card manager with comprehensive data display"""
        try:
            from advanced_card_manager_ui import AdvancedCardManagerUI
            
            # Create and show advanced card manager
            self.advanced_card_manager = AdvancedCardManagerUI()
            
            # If there's a current card, process it immediately
            current_card = self.cards.get_current_card()
            if current_card:
                try:
                    # Export current card data for comprehensive analysis
                    card_data = {
                        "pan": current_card.get_cardholder_info().get("PAN", "4111111111111111"),
                        "cardholder_name": current_card.get_cardholder_info().get("Name", "CARD HOLDER"),
                        "expiry": current_card.get_cardholder_info().get("Expiry", "2512"),
                        "service_code": current_card.get_cardholder_info().get("Service Code", "201"),
                        "pin": "6998",  # Actual PIN from current card on reader
                        "cvv": current_card.get_cardholder_info().get("CVV", "123"),
                        "track2": current_card.get_cardholder_info().get("Track2", ""),
                        "transactions": getattr(current_card, 'transactions', []),
                        "apdu_log": getattr(current_card, 'apdu_log', []),
                        "tlv_data": getattr(current_card, 'tlv_root', {}),
                        "cryptograms": getattr(current_card, 'cryptograms', {}),
                        "encrypted_data": getattr(current_card, 'encrypted_pin_blocks', []),
                        "issuer": current_card.get_cardholder_info().get("Issuer", "Unknown"),
                        "country": "Unknown",
                        "currency": "USD",
                        "card_type": "VISA"
                    }
                    
                    # Extract and add the current card data to manager
                    extracted_data = self.advanced_card_manager.card_manager.extract_complete_card_data(card_data)
                    self.advanced_card_manager.card_manager.add_card(extracted_data)
                    self.advanced_card_manager.updateCardDropdown()
                    
                    self.logger.log("[MainWindow] Current card loaded into Advanced Card Manager", "INFO")
                    
                except Exception as e:
                    self.logger.log(f"[MainWindow] Could not load current card into manager: {e}", "WARN")
            
            # Show the advanced card manager
            self.advanced_card_manager.show()
            
        except ImportError as e:
            self.logger.log(f"[MainWindow] Advanced Card Manager not available: {e}", "ERROR")
            try:
                QtWidgets = importlib.import_module('PyQt5.QtWidgets')
                QtWidgets.QMessageBox.warning(self, "Import Error", f"Advanced Card Manager not available: {e}")
            except Exception:
                pass
        except Exception as e:
            self.logger.log(f"[MainWindow] Failed to open Advanced Card Manager: {e}", "ERROR")
            try:
                QtWidgets = importlib.import_module('PyQt5.QtWidgets')
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to open Advanced Card Manager: {e}")
            except Exception:
                pass

    def on_msr_write(self):
        card = self.cards.get_current_card()
        if not card:
            QMessageBox.warning(self, "MSR Write", "No card selected")
            return
        track2 = card.track_data.get("Track2", "")
        self.magstripe_writer.write(track2=track2, device=self._get_selected_msr_device())

    def on_magspoof_downgrade(self):
        """Enhanced EMV to magstripe conversion using the enhanced writer"""
        card = self.cards.get_current_card()
        if not card:
            self.show_status("No card selected for EMV Conversion", 5000)
            QMessageBox.warning(self, "EMV Conversion", "No card selected")
            return
        
        # Get card information
        card_info = card.get_cardholder_info() if hasattr(card, 'get_cardholder_info') else {}
        track2 = card.track_data.get("Track2", "")
        
        if not track2:
            self.show_status("No Track 2 data available", 5000)
            QMessageBox.warning(self, "EMV Conversion", "No Track 2 data available for conversion")
            return
            
        try:
            self.show_status("Converting EMV card to magstripe format...", 3000)
            
            # Use enhanced writer for conversion
            card_data = {
                'track2': track2,
                'cardholder_info': card_info
            }
            
            conversion_result = self.enhanced_magstripe_writer.convert_emv_to_magstripe(
                card_data=card_data,
                target_service_code="101",  # Convert to magstripe-preferred
                pin="1337",
                embed_pin=True
            )
            
            if not conversion_result:
                self.show_status("EMV conversion failed", 5000)
                QMessageBox.warning(self, "EMV Conversion", "EMV to magstripe conversion failed")
                return
                
            # Show conversion details
            original_service = conversion_result.get('original_service_code', 'Unknown')
            new_service = conversion_result.get('new_service_code', 'Unknown') 
            original_cvv = conversion_result.get('original_cvv', 'Unknown')
            new_cvv = conversion_result.get('new_cvv', 'Unknown')
            
            conversion_msg = f"""EMV Conversion Complete:
            
Service Code: {original_service} → {new_service}
CVV: {original_cvv} → {new_cvv}
PIN: 1337 (embedded)

New card will bypass EMV chip and force magstripe transactions."""
            
            self.show_status(f"Conversion complete: {original_service}→{new_service}, CVV: {original_cvv}→{new_cvv}", 5000)
            
            # Ask user if they want to write to device
            reply = QMessageBox.question(
                self, 
                "EMV Conversion Complete",
                conversion_msg + "\n\nWrite converted card to magstripe device now?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Write to device
                device = self._get_selected_msr_device()
                success = self.enhanced_magstripe_writer.write_converted_card(
                    conversion_result, 
                    device=device
                )
                
                if success:
                    self.show_status("Enhanced magstripe write successful!", 5000)
                    QMessageBox.information(self, "Write Complete", "Enhanced magstripe write successful!\n\nCard is now magstripe-preferred (101) with PIN 1337.")
                else:
                    self.show_status("Magstripe write failed", 5000)
                    QMessageBox.warning(self, "Write Failed", "Failed to write to magstripe device")
            else:
                QMessageBox.information(self, "Conversion Complete", "EMV conversion completed successfully.\nUse 'MSR Write' to write the data later.")
                
        except Exception as e:
            error_msg = f"EMV conversion error: {str(e)}"
            self.show_status(error_msg, 5000)
            QMessageBox.critical(self, "Conversion Error", error_msg)
            self.logger.error(f"Enhanced magstripe conversion failed: {e}")

    def on_bulk_ac(self):
        card = self.cards.get_current_card()
        if not card:
            QMessageBox.warning(self, "Bulk AC", "No card selected")
            return
        count, ok = BulkACRunner.prompt_bulk_count(self)
        if ok:
            logs = self.bulk_ac.run(card, count)
            for log in logs:
                self.ui.txtAPDU.append(log)

    def show_reader_indicator(self, connected: bool):
        color = "green" if connected else "red"
        self.ui.readerIndicator.setStyleSheet(
            f"background-color: {color}; border-radius: 6px;"
        )
        self.ui.readerIndicator.setFixedSize(12, 12)

    def show_bluetooth_indicator(self, status: str):
        icons = {
            "connected": ":/icons/bt_connected.png",
            "paired": ":/icons/bt_paired.png",
            "disconnected": ":/icons/bt_disconnected.png"
        }
        icon = icons.get(status, icons["disconnected"])
        pix = QIcon(icon).pixmap(16, 16)
        self.ui.btIndicator.setPixmap(pix)

    # ---------- Cardhopper wiring ----------
    def _wire_cardhopper(self):
        self.ui.btnCHConnect.clicked.connect(self.on_cardhopper_connect)
        self.ui.btnCHDisconnect.clicked.connect(self.on_cardhopper_disconnect)
        self.ui.btnCHStart.clicked.connect(self.on_cardhopper_start)
        self.ui.btnCHStartServer.clicked.connect(self.on_cardhopper_start_server)
        self.ui.btnCHStopServer.clicked.connect(self.on_cardhopper_stop_server)
        self.ui.btnCHBatchStart.clicked.connect(self.on_cardhopper_batch_start)
        self.ui.btnCHBatchStop.clicked.connect(self.on_cardhopper_batch_stop)

        self._ch_pm_port = self.settings.get("proxmark_port", "/dev/ttyACM0")
        self._ch = None

    def on_cardhopper_connect(self):
        self._ch = CardhopperRelay(logger=self.logger, pm_port=self._ch_pm_port)
        self.ui.lblCHStatus.setText("Cardhopper: connected")

    def on_cardhopper_disconnect(self):
        # For now just update UI; connection is serial managed by Proxmark3Manager
        self._ch = None
        self.ui.lblCHStatus.setText("Cardhopper: disconnected")

    def on_cardhopper_start(self):
        # decide backend by UI selection
        dev = self.ui.cmbCHDevice.currentText() if hasattr(self.ui, 'cmbCHDevice') else "Proxmark3"
        if dev in ("Proxmark3", "Auto"):
            if not self._ch:
                self.on_cardhopper_connect()
            self.logger.log("[Cardhopper] Relay active (Proxmark3)")
            self.ui.lblCHStatus.setText("Cardhopper: relay active (Proxmark3)")
        elif dev in ("PCSC", "ACR"):
            # fall back to existing relay dialog for PC/SC devices
            self.on_relay_card()
            self.ui.lblCHStatus.setText("Relay (PC/SC) active")
        elif dev == "PN532":
            # fall back to existing PN532 relay flow
            self.on_relay_card()
            self.ui.lblCHStatus.setText("Relay (PN532) active")
        elif dev == "Chameleon":
            # use chameleon manager for emulation/relay
            try:
                from chameleon_manager import ChameleonManager
                self._cham = ChameleonManager(self.logger)
                self._cham.start_emulation()
                self.ui.lblCHStatus.setText("Chameleon emulation active")
                self.logger.log("[Cardhopper] Chameleon emulation active")
            except Exception as e:
                self.logger.log(f"[Cardhopper] Chameleon error: {e}", "ERROR")
        else:
            self.logger.log("[Cardhopper] Unknown device selection", "WARN")

    def on_cardhopper_start_server(self):
        if not self._ch:
            self._ch = CardhopperRelay(logger=self.logger, pm_port=self._ch_pm_port,
                                       server_host="0.0.0.0", server_port=9000)
        else:
            self._ch.pm.start_cardhopper_server("0.0.0.0", 9000)
        self.logger.log("[Cardhopper] Server listening 0.0.0.0:9000")
        self.ui.lblCHStatus.setText("Cardhopper: server running")

    def on_cardhopper_stop_server(self):
        if self._ch:
            self._ch.pm.stop_cardhopper_server()
        self.ui.lblCHStatus.setText("Cardhopper: connected")

    def on_cardhopper_batch_start(self):
        self.logger.log("[Cardhopper] Batch start requested")

    def on_cardhopper_batch_stop(self):
        self.logger.log("[Cardhopper] Batch stop requested")

    def on_show_credits(self):
        text = (
            "nfsp00f3r V4.05 integrated credits:\n"
            "- Cardhopper — Tiernan Messmer (Neo-Vortex) — GPL v3+\n"
            "- proxmark3 — RfidResearchGroup — GPL v3\n"
            "- danmichaelo/emv — MIT; dimalinux/EMV-Tools — GPLv3; atzedevs/emv-crypto — MIT\n"
            "- Yagoor/EMV — GPL v3; EMV-NFC-Paycard-Reader — GPL v3\n"
            "- python-pyscard — GPL v2; RFIDIOt — GPL v2; RFIDIOt/preplayattack — GPL v2\n"
            "- destroythedrones/* — various; openemv — GPL v3; TalkToYourCreditCardPart7 — GPL v3"
        )
        QMessageBox.information(self, "Credits", text)
