# pos_client.py
import sys
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sqlite3
from datetime import datetime
from cart_dialog import CartDialog
import os # For checking if icons exist
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

class Product:
    def __init__(self, code, name, description, price, quantity, cost_price):
        self.code = code
        self.name = name
        self.description = description
        self.price = price
        self.quantity = quantity
        self.cost_price = cost_price

class POSClient(QWidget):
    def __init__(self):
        super().__init__()
        self.db = sqlite3.connect('pos.db')
        self.cursor = self.db.cursor()
        self.init_db()
        
        self.products = self.load_products()
        self.cart = []
        self.cashier_name = ""  # Store cashier name
        self.initUI()
        self.update_product_combo()

        self._current_product_codes = {p.code for p in self.products}

        self.check_for_new_products_timer = QTimer(self)
        self.check_for_new_products_timer.setInterval(5000)
        self.check_for_new_products_timer.timeout.connect(self._check_for_new_products)
        self.check_for_new_products_timer.start()

    def init_db(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                cost_price REAL NOT NULL DEFAULT 0.00
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT,
                quantity INTEGER,
                sale_price REAL,
                cost_at_sale REAL,
                sale_date TEXT
            )
        ''')
        try:
            self.cursor.execute("ALTER TABLE products ADD COLUMN cost_price REAL NOT NULL DEFAULT 0.00")
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute("ALTER TABLE sales ADD COLUMN cost_at_sale REAL NOT NULL DEFAULT 0.00")
        except sqlite3.OperationalError:
            pass
            
        self.db.commit()

    def get_icon(self, icon_name):
        path = os.path.join('icons', icon_name)
        if os.path.exists(path):
            return QIcon(path)
        return QIcon() # Return empty icon if not found

    def initUI(self):
        self.setWindowTitle('Point of Sale System')
        self.setGeometry(100, 100, 1000, 300)

        # Main stacked widget for transitions
        self.stacked_widget = QStackedWidget()
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        # --- POS Main Page ---
        self.pos_page = QWidget()
        pos_layout = QHBoxLayout(self.pos_page)
        
        # Left Section: Product Selection & Cart Button
        left_panel = QVBoxLayout()
        pos_layout.addLayout(left_panel, 2)

        product_selection_group = QGroupBox("New Sale")
        product_layout = QGridLayout()
        product_selection_group.setLayout(product_layout)
        product_selection_group.setFont(QFont("Segoe UI", 12, QFont.Bold))

        product_layout.addWidget(QLabel('Product:'), 0, 0)
        self.product_combo = QComboBox()
        self.product_combo.setFont(QFont("Segoe UI", 11))
        self.product_combo.currentIndexChanged.connect(self.display_selected_product_info)
        product_layout.addWidget(self.product_combo, 0, 1)

        product_layout.addWidget(QLabel('Quantity:'), 1, 0)
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999)
        self.quantity_input.setFont(QFont("Segoe UI", 11))
        product_layout.addWidget(self.quantity_input, 1, 1)

        product_layout.addWidget(QLabel('Unit Price:'), 2, 0)
        self.unit_price_label = QLabel('R0.00')
        self.unit_price_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        product_layout.addWidget(self.unit_price_label, 2, 1)

        add_to_cart_button = QPushButton('Add to Cart')
        add_to_cart_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        add_to_cart_button.setIcon(self.get_icon('add_to_cart.png'))
        add_to_cart_button.clicked.connect(self.add_to_cart)
        product_layout.addWidget(add_to_cart_button, 3, 0, 1, 2)

        left_panel.addWidget(product_selection_group)
        left_panel.addStretch()

        view_cart_button = QPushButton('View Cart')
        view_cart_button.setFont(QFont("Segoe UI", 12, QFont.Bold))
        view_cart_button.setIcon(self.get_icon('view_cart.png'))
        view_cart_button.setStyleSheet("background-color: #007bff;")
        view_cart_button.clicked.connect(self.show_cart_dialog)
        left_panel.addWidget(view_cart_button)

        # Right Section: Slip Display and Print
        right_panel = QVBoxLayout()
        pos_layout.addLayout(right_panel, 1)

        slip_display_group = QGroupBox("Sale Slip / Receipt")
        slip_layout = QVBoxLayout()
        slip_display_group.setLayout(slip_layout)
        slip_display_group.setFont(QFont("Segoe UI", 12, QFont.Bold))

        self.slip_text_display = QTextEdit()
        self.slip_text_display.setReadOnly(True)
        self.slip_text_display.setFont(QFont("Consolas", 9))
        slip_layout.addWidget(self.slip_text_display)

        self.print_slip_button = QPushButton("Print Slip")
        self.print_slip_button.setIcon(self.get_icon('print.png'))
        self.print_slip_button.setStyleSheet("background-color: #6c757d;")
        self.print_slip_button.clicked.connect(self.print_slip)
        self.print_slip_button.setEnabled(False)
        slip_layout.addWidget(self.print_slip_button)

        right_panel.addWidget(slip_display_group)

        # --- Cart Page ---
        self.cart_page = QWidget()
        cart_layout = QVBoxLayout(self.cart_page)
        
        # Back button
        back_button = QPushButton('← Back to POS')
        back_button.setFont(QFont("Segoe UI", 12, QFont.Bold))
        back_button.setIcon(self.get_icon('back.png'))
        back_button.setStyleSheet("background-color: #6c757d;")
        back_button.clicked.connect(self.hide_cart_dialog)
        cart_layout.addWidget(back_button)

        # Cart widget will be added here dynamically
        self.cart_widget_placeholder = QVBoxLayout()
        cart_layout.addLayout(self.cart_widget_placeholder)

        # Add both pages to stacked widget
        self.stacked_widget.addWidget(self.pos_page)
        self.stacked_widget.addWidget(self.cart_page)

        # Apply stylesheet
        self.setStyleSheet("""
            QWidget {
                background-color: #e0e6ed;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                border: 2px solid #aebac9;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #ffffff;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #e0e6ed;
                border-radius: 5px;
            }
            QLabel {
                color: #333333;
                font-size: 11pt;
            }
            QPushButton {
                background-color: #007bff;
                color: #ffffff;
                padding: 10px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                icon-size: 20px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QComboBox, QLineEdit, QSpinBox {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 5px;
                background-color: #f8f9fa;
            }
            QTextEdit {
                border: 1px solid #ced4da;
                border-radius: 5px;
                background-color: #ffffff;
                padding: 10px;
            }
        """)

    def load_products(self):
        self.cursor.execute('SELECT code, name, description, price, quantity, cost_price FROM products')
        rows = self.cursor.fetchall()
        products = []
        for row in rows:
            products.append(Product(row[0], row[1], row[2], row[3], row[4], row[5]))
        return products

    def update_product_combo(self):
        current_code = self.product_combo.currentData()
        
        self.product_combo.clear()
        if not self.products:
            self.product_combo.addItem("No Products Available")
            self.product_combo.setEnabled(False)
            self.quantity_input.setEnabled(False)
            self.unit_price_label.setText("R0.00")
            return
        
        self.product_combo.setEnabled(True)
        self.quantity_input.setEnabled(True)
        for product in self.products:
            self.product_combo.addItem(product.name, product.code)

        if current_code in {p.code for p in self.products}:
            index = self.product_combo.findData(current_code)
            if index != -1:
                self.product_combo.setCurrentIndex(index)
        else:
            self.product_combo.setCurrentIndex(0)

        self.display_selected_product_info()

    def display_selected_product_info(self):
        selected_product_code = self.product_combo.currentData()
        if selected_product_code:
            product = next((p for p in self.products if p.code == selected_product_code), None)
            if product:
                self.unit_price_label.setText(f'R{product.price:.2f}')
                self.quantity_input.setMaximum(product.quantity)
                if product.quantity == 0:
                    self.quantity_input.setEnabled(False)
                    if self.product_combo.currentText() == product.name:
                        QMessageBox.warning(self, 'Out of Stock', f'{product.name} is currently out of stock.')
                else:
                    self.quantity_input.setEnabled(True)
                    self.quantity_input.setValue(1)
            else:
                self.unit_price_label.setText('R0.00')
                self.quantity_input.setEnabled(False)
        else:
            self.unit_price_label.setText('R0.00')
            self.quantity_input.setEnabled(False)

    def add_to_cart(self):
        product_name = self.product_combo.currentText()
        product_code = self.product_combo.currentData()
        if not product_code or product_name == "No Products Available":
            QMessageBox.warning(self, 'No Product Selected', 'Please select a product to add to cart.')
            return

        try:
            quantity_to_add = self.quantity_input.value()
            
            self.products = self.load_products() 
            product = next((p for p in self.products if p.code == product_code), None)

            if not product:
                QMessageBox.critical(self, 'Error', 'Selected product not found in inventory.')
                self.update_product_combo()
                return

            if quantity_to_add <= 0:
                QMessageBox.warning(self, 'Invalid Quantity', 'Quantity must be a positive number.')
                return

            if quantity_to_add > product.quantity:
                QMessageBox.warning(self, 'Insufficient Stock',
                                    f'Only {product.quantity} of {product.name} available in stock.')
                return

            found_in_cart = False
            for item in self.cart:
                if item['product_code'] == product_code:
                    if item['quantity'] + quantity_to_add > product.quantity:
                        QMessageBox.warning(self, 'Insufficient Stock',
                                            f'Adding this quantity would exceed available stock for {product.name}. You currently have {item["quantity"]} in cart, and there are {product.quantity} in total stock.')
                        return
                    item['quantity'] += quantity_to_add
                    found_in_cart = True
                    break
            
            if not found_in_cart:
                self.cart.append({
                    'product_code': product.code,
                    'product_name': product.name,
                    'price': product.price,
                    'cost_price': product.cost_price,
                    'quantity': quantity_to_add
                })
            
            self.quantity_input.setValue(1)
            QMessageBox.information(self, 'Cart Updated', f'{quantity_to_add} x {product.name} added to cart.')
            self.slip_text_display.clear() # Clear slip display when adding new items
            self.print_slip_button.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An unexpected error occurred: {e}')

    def show_cart_dialog(self):
        # Create cart dialog but don't show it as separate window
        self.cart_dialog = CartDialog(self.db, self.cart, parent=self)
        
        # Clear previous cart widget
        for i in reversed(range(self.cart_widget_placeholder.count())): 
            widget = self.cart_widget_placeholder.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        
        # Add cart dialog's layout to our cart page
        self.cart_widget_placeholder.addWidget(self.cart_dialog)
        
        # Slide to cart page
        self.stacked_widget.setCurrentIndex(1)

    def hide_cart_dialog(self):
        # Slide back to POS page
        self.stacked_widget.setCurrentIndex(0)

    def on_sale_processed(self, processed_items, final_total):
        """Called when a sale is successfully processed from the cart dialog"""
        self.products = self.load_products() 
        self.update_product_combo() 
        
        self.display_sale_slip(processed_items, final_total)
        self.print_slip_button.setEnabled(True)

        self.cart = [] # Clear the main client's cart list after successful sale
        self.hide_cart_dialog() # Return to POS view

    def prompt_cashier_name(self):
        """Prompt for cashier name before printing slip"""
        name, ok = QInputDialog.getText(self, 'Cashier Name', 
                                       'Enter your name for the receipt:',
                                       QLineEdit.Normal, '')
        if ok and name.strip():
            return name.strip()
        else:
            return "Cashier"

    def display_sale_slip(self, sales_items, total_amount):
        """Generates and displays a text-based sales slip for the given sales_items."""
        slip_text = []
        
        current_datetime = datetime.now()
        sale_date_time = current_datetime.strftime('%d.%m.%y %H:%M')
        
        # Header - RESTORED ORIGINAL FORMATTING
        slip_text.append("=" * 27)
        slip_text.append(f"{'SERENITY':^60}") # Center store name
        slip_text.append(f"{'Where every purchase is a winning move.':36}")
        slip_text.append("\n")
        slip_text.append(f"{'CLEREMONT':^60}") # Center town
        
        # Use system username as default, will be replaced when printing
        cashier_id = os.environ.get('USERNAME', 'Guest').upper()
        slip_text.append(f"CASHIER ID: {cashier_id:>{40 - len('CASHIER ID: ')}}") # Align cashier ID to left, fill rest with space
        
        slip_text.append("-" * 50)
        # Item Header: QTY on left, ITEM name in middle, PRICE on right
        slip_text.append(f"{'QTY':<8}{'ITEM':<19}{'PRICE':>20}")
        slip_text.append("-" * 50)

        total_vat_incl = 0.0
        
        for item in sales_items: # Iterate through the actual items from the processed cart
            product_name = item['product_name']
            quantity = item['quantity']
            unit_price = item['price']
            subtotal = quantity * unit_price
            total_vat_incl += subtotal # Accumulate total for VAT calculation
            
            # Format each item line: QTY ITEM_NAME PRICE
            # Ensure product_name is truncated if too long to fit
            display_name = product_name
            max_name_len = 39 - 4 - 11 # SLIP_WIDTH - len('QTY ') - len(' PRICE')
            if len(display_name) > max_name_len:
                display_name = display_name[:max_name_len-3] + '...' # Truncate and add ellipsis

            slip_text.append(f"{quantity:<8}{display_name:<}{subtotal:>20.2f}")
            
        slip_text.append("-" * 50)
        
        # Totals and VAT
        vat_rate = 0.15 # 15% VAT for South Africa
        vat_amount = total_vat_incl * (vat_rate)
        total_amount = total_vat_incl + vat_amount
        
        # Note: The original Boxer slip shows "NON SUPPLY EXCL VAT" as the total *before* VAT.
        # If your `total_amount` passed from CartDialog is the VAT-inclusive total, 
        # then `total_vat_incl` will be that value.
        # Let's align with the sample and assume `total_amount` is the final R-value.
        
        slip_text.append(f"{'SUBTOTAL:':<{60 - 12}}{total_vat_incl:>5.2f}")
        slip_text.append(f"{'VAT (15%):':<{46 - 12}}{vat_amount:>14.2f}")
        slip_text.append(f"{'VAT REG NO.':<{50 - len('4450203302')}}{'4450203302':>}") # Example VAT number

        slip_text.append("=" * 27)
        slip_text.append(f"{'TOTAL:':<{60 - 9}}R{total_amount:>1.2f}") # Use total_amount from CartDialog
        slip_text.append("=" * 27)
        
        # Footer
        slip_text.append(f"\n{'THANK YOU FOR SHOPPING WITH US!':^36}")
        slip_text.append(f"{'TAX INVOICE':^57}")
        slip_text.append(f"{'PO Box 370, Cleremont, 4000':^46}") # Updated address example
        slip_text.append(f"{'RSA':^65}")
        slip_text.append(f"\n{'Add Us on WhatsApp':^55}")
        slip_text.append(f"{'065 585 1524':^60}\n") # Example number

        slip_text.append(f"{'PROMOTIONAL COUPON':^40}")
        slip_text.append(f"{'CAMPAIGN:':<16}{'393700000CP':>27}") # Example values
        slip_text.append(f"{'REFERENCE:':<16}{'263300000XP':>28}") # Example values
        slip_text.append(f"\n{'STAND A CHANCE TO WIN!':^42}")
        slip_text.append(f"{'120*2637*5463*1520#':^46}") # Shortened example
        slip_text.append(f"{'Double your CASH BACK at SERENITY':^40}")
        slip_text.append(f"{'Because you bought Qualifying Item/s*':^40}")
        
        slip_text.append(f"SA Time: {sale_date_time:>{53 - len('SA Time: ')}}") # Date and Time aligned left
        slip_text.append("-" * 50) # Example of receipt number/transaction ID
        slip_text.append(f"TRN: {current_datetime.strftime('%Y%m%d%H%M%S'):>46}") # Simple transaction number
        slip_text.append("-" *50)

        self.slip_text_display.setText("\n".join(slip_text))

    def get_product_name_from_code(self, code):
        """Helper to get product name from code. Could be optimized."""
        product = next((p for p in self.products if p.code == code), None)
        return product.name if product else "Unknown Item"

    def print_slip(self):
        """Print slip with cashier name prompt - ASK EVERY TIME"""
        # Always ask for cashier name before printing
        cashier_name = self.prompt_cashier_name()
        
        if cashier_name:
            # Update the slip display with the new cashier name
            current_slip = self.slip_text_display.toPlainText()
            # Replace the cashier line with the new name
            lines = current_slip.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('CASHIER ID:'):
                    lines[i] = f"CASHIER ID: {cashier_name.upper():>{40 - len('CASHIER ID: ')}}"
                    break
            
            updated_slip = '\n'.join(lines)
            self.slip_text_display.setText(updated_slip)
            
            printer = QPrinter(QPrinter.HighResolution)
            print_dialog = QPrintDialog(printer, self)
            if print_dialog.exec_() == QPrintDialog.Accepted:
                self.slip_text_display.print_(printer)

    def _check_for_new_products(self):
        latest_products = self.load_products()
        latest_product_codes = {p.code for p in latest_products}

        new_product_codes = latest_product_codes - self._current_product_codes

        if new_product_codes:
            new_items_info = []
            for code in new_product_codes:
                new_product = next((p for p in latest_products if p.code == code), None)
                if new_product:
                    new_items_info.append(f"{new_product.name} (R{new_product.price:.2f})")
            
            if new_items_info:
                QMessageBox.information(self, 'New Items Available!',
                                        'We have new items available:\n' + '\n'.join(new_items_info))
            
            self.products = latest_products
            self.update_product_combo()
            self._current_product_codes = latest_product_codes
        
        elif len(latest_products) != len(self.products) or \
             any(p.quantity != next((op.quantity for op in self.products if op.code == p.code), None) or \
                 p.price != next((op.price for op in self.products if op.code == p.code), None) or \
                 p.cost_price != next((op.cost_price for op in self.products if op.code == p.code), None) \
                 for p in latest_products if p.code in self._current_product_codes):
            self.products = latest_products
            self.update_product_combo()
            self._current_product_codes = latest_product_codes


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    conn = sqlite3.connect('pos.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            cost_price REAL NOT NULL DEFAULT 0.00
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT,
            quantity INTEGER,
            sale_price REAL,
            cost_at_sale REAL,
            sale_date TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN cost_price REAL NOT NULL DEFAULT 0.00")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE sales ADD COLUMN cost_at_sale REAL NOT NULL DEFAULT 0.00")
    except sqlite3.OperationalError:
        pass
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        print("Inserting sample products...")
        cursor.execute("INSERT INTO products (code, name, description, price, quantity, cost_price) VALUES (?, ?, ?, ?, ?, ?)",
                       ('APP001', 'Apple', 'Fresh Red Apple', 5.50, 100, 3.00))
        cursor.execute("INSERT INTO products (code, name, description, price, quantity, cost_price) VALUES (?, ?, ?, ?, ?, ?)",
                       ('BAN002', 'Banana', 'Yellow Banana', 3.00, 150, 1.50))
        cursor.execute("INSERT INTO products (code, name, description, price, quantity, cost_price) VALUES (?, ?, ?, ?, ?, ?)",
                       ('MILK003', 'Milk (1L)', 'Full Cream Milk', 22.99, 50, 18.00))
        conn.commit()
    conn.close()

    pos_system = POSClient()
    pos_system.show()
    sys.exit(app.exec_())