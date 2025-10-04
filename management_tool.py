# management_tool.py
import sys
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sqlite3
from datetime import datetime

class Product:
    def __init__(self, code, name, description, price, quantity, cost_price): # Added cost_price
        self.code = code
        self.name = name
        self.description = description
        self.price = price
        self.quantity = quantity
        self.cost_price = cost_price

class ManagementTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = sqlite3.connect('pos.db')
        self.cursor = self.db.cursor()
        self.init_db() 
        self.products = self.load_products()
        
        # Initialize financial metrics
        self.total_revenue = 0.0
        self.total_cogs = 0.0
        self.total_profit = 0.0
        self.available_profit_for_allocation = 0.0

        self.initUI()
        self.refresh_product_table()
        self.refresh_sales_table() # This will also calculate initial metrics
        
        # QTimer for Sales History Polling
        self.check_for_new_sales_timer = QTimer(self)
        self.check_for_new_sales_timer.setInterval(5000)
        self.check_for_new_sales_timer.timeout.connect(self._auto_refresh_data) # New auto-refresh method
        self.check_for_new_sales_timer.start()

    def init_db(self):
        # Ensure 'cost_price' column exists in products table.
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                cost_price REAL NOT NULL DEFAULT 0.00 -- NEW: Added cost_price
            )
        ''')
        # Ensure 'cost_at_sale' is in the sales table.
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT,
                quantity INTEGER,
                sale_price REAL,
                cost_at_sale REAL, -- NEW: Added cost of product at time of sale
                sale_date TEXT
            )
        ''')
        # Add column if it doesn't exist for existing databases (simple migration)
        try:
            self.cursor.execute("ALTER TABLE products ADD COLUMN cost_price REAL NOT NULL DEFAULT 0.00")
        except sqlite3.OperationalError:
            pass # Column already exists
        try:
            self.cursor.execute("ALTER TABLE sales ADD COLUMN cost_at_sale REAL NOT NULL DEFAULT 0.00")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        self.db.commit()

    def initUI(self):
        self.setWindowTitle('POS Management Tools')
        self.setGeometry(150, 150, 1100, 750) # Increased size
        self.setWindowIcon(QIcon('icons/management.png'))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Product Management Section ---
        product_management_group = QGroupBox("Product Management")
        product_management_layout = QVBoxLayout()
        product_management_group.setLayout(product_management_layout)
        product_management_group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        main_layout.addWidget(product_management_group)

        self.product_table = QTableWidget()
        self.product_table.setColumnCount(6) # Increased column count for cost_price
        self.product_table.setHorizontalHeaderLabels(['Code', 'Name', 'Description', 'Sale Price (R)', 'Cost Price (R)', 'Quantity'])
        self.product_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.product_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.horizontalHeader().setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.product_table.setFont(QFont("Segoe UI", 10))
        product_management_layout.addWidget(self.product_table)

        product_button_layout = QHBoxLayout()
        add_product_button = QPushButton('Add New Product')
        add_product_button.setIcon(QIcon('icons/add_product.png'))
        add_product_button.clicked.connect(self.add_product_dialog)
        product_button_layout.addWidget(add_product_button)

        edit_product_button = QPushButton("Edit Selected Product")
        edit_product_button.setIcon(QIcon('icons/edit.png'))
        edit_product_button.clicked.connect(self.edit_product)
        product_button_layout.addWidget(edit_product_button)

        delete_product_button = QPushButton("Delete Selected Product")
        delete_product_button.setIcon(QIcon('icons/delete.png'))
        delete_product_button.setStyleSheet("background-color: #dc3545;")
        delete_product_button.clicked.connect(self.delete_product)
        product_button_layout.addWidget(delete_product_button)
        product_management_layout.addLayout(product_button_layout)

        # --- Sales History Section ---
        sales_history_group = QGroupBox("Sales History")
        sales_history_layout = QVBoxLayout()
        sales_history_group.setLayout(sales_history_layout)
        sales_history_group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        main_layout.addWidget(sales_history_group)

        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(6) # Increased column count for cost_at_sale
        self.sales_table.setHorizontalHeaderLabels(['Sale ID', 'Product Code', 'Quantity', 'Revenue (R)', 'Cost (R)', 'Date'])
        self.sales_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sales_table.horizontalHeader().setStretchLastSection(True)
        self.sales_table.horizontalHeader().setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.sales_table.setFont(QFont("Segoe UI", 10))
        sales_history_layout.addWidget(self.sales_table)

        # --- Financial Overview Section ---
        financial_group = QGroupBox("Financial Overview")
        financial_layout = QVBoxLayout()
        financial_group.setLayout(financial_layout)
        financial_group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        main_layout.addWidget(financial_group)

        metrics_layout = QGridLayout()
        metrics_layout.setContentsMargins(10,10,10,10)

        metrics_layout.addWidget(QLabel("Total Revenue:"), 0, 0)
        self.revenue_label = QLabel("R0.00")
        self.revenue_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.revenue_label.setStyleSheet("color: #007bff;")
        metrics_layout.addWidget(self.revenue_label, 0, 1)

        metrics_layout.addWidget(QLabel("Total Cost of Goods Sold:"), 1, 0)
        self.cogs_label = QLabel("R0.00")
        self.cogs_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.cogs_label.setStyleSheet("color: #dc3545;")
        metrics_layout.addWidget(self.cogs_label, 1, 1)

        metrics_layout.addWidget(QLabel("Total Gross Profit:"), 2, 0)
        self.profit_label = QLabel("R0.00")
        self.profit_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.profit_label.setStyleSheet("color: #28a745;")
        metrics_layout.addWidget(self.profit_label, 2, 1)

        metrics_layout.addWidget(QLabel("Available for Allocation:"), 3, 0)
        self.available_profit_label = QLabel("R0.00")
        self.available_profit_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.available_profit_label.setStyleSheet("color: #6f42c1;") # Purple color
        metrics_layout.addWidget(self.available_profit_label, 3, 1)

        financial_layout.addLayout(metrics_layout)

        # --- Profit Allocation Buttons ---
        profit_allocation_buttons_layout = QHBoxLayout()
        allocate_profit_button = QPushButton("Allocate Profit")
        allocate_profit_button.setIcon(QIcon('icons/allocate_profit.png')) # You'll need this icon
        allocate_profit_button.clicked.connect(self.allocate_profit_dialog)
        profit_allocation_buttons_layout.addWidget(allocate_profit_button)
        
        # Reset Allocation (optional, but good for testing)
        reset_allocation_button = QPushButton("Reset Allocation")
        reset_allocation_button.setIcon(QIcon('icons/reset.png')) # You'll need this icon
        reset_allocation_button.setStyleSheet("background-color: #ffc107; color: #333;")
        reset_allocation_button.clicked.connect(self.reset_profit_allocation)
        profit_allocation_buttons_layout.addWidget(reset_allocation_button)

        financial_layout.addLayout(profit_allocation_buttons_layout)


        # --- Control Buttons for Sales History ---
        sales_button_layout = QHBoxLayout()
        sales_button_layout.addStretch() # Push buttons to the right
        clear_sales_button = QPushButton("Clear All Sales History")
        clear_sales_button.setIcon(QIcon('icons/clear_history.png'))
        clear_sales_button.setStyleSheet("background-color: #dc3545;")
        clear_sales_button.clicked.connect(self.clear_sales_history)
        sales_button_layout.addWidget(clear_sales_button)
        sales_history_layout.addLayout(sales_button_layout)


        self.setStyleSheet("""
            QMainWindow {
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
            QPushButton#qt_resetAllocationButton:hover {
                background-color: #e0a800;
            }
            QTableWidget {
                border: 1px solid #ced4da;
                border-radius: 5px;
                background-color: #ffffff;
                gridline-color: #e9ecef;
            }
            QHeaderView::section {
                background-color: #f2f2f2;
                padding: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)

    def load_products(self):
        # Retrieve cost_price along with other product details
        self.cursor.execute('SELECT code, name, description, price, quantity, cost_price FROM products')
        rows = self.cursor.fetchall()
        products = []
        for row in rows:
            products.append(Product(row[0], row[1], row[2], row[3], row[4], row[5]))
        return products

    def refresh_product_table(self):
        self.products = self.load_products()
        self.product_table.setRowCount(len(self.products))
        for i, product in enumerate(self.products):
            self.product_table.setItem(i, 0, QTableWidgetItem(product.code))
            self.product_table.setItem(i, 1, QTableWidgetItem(product.name))
            self.product_table.setItem(i, 2, QTableWidgetItem(product.description))
            self.product_table.setItem(i, 3, QTableWidgetItem(f'{product.price:.2f}'))
            self.product_table.setItem(i, 4, QTableWidgetItem(f'{product.cost_price:.2f}')) # Display cost_price
            self.product_table.setItem(i, 5, QTableWidgetItem(str(product.quantity)))
        self.product_table.resizeColumnsToContents()

    def refresh_sales_table(self):
        """
        Reloads sales data, updates the sales table, and recalculates financial metrics.
        """
        self.cursor.execute('SELECT sale_id, product_code, quantity, sale_price, cost_at_sale, sale_date FROM sales ORDER BY sale_date DESC')
        rows = self.cursor.fetchall()
        
        self.sales_table.setRowCount(len(rows))
        self.total_revenue = 0.0
        self.total_cogs = 0.0

        for i, row in enumerate(rows):
            sale_id, product_code, quantity, sale_price, cost_at_sale, sale_date = row
            self.sales_table.setItem(i, 0, QTableWidgetItem(str(sale_id)))
            self.sales_table.setItem(i, 1, QTableWidgetItem(product_code))
            self.sales_table.setItem(i, 2, QTableWidgetItem(str(quantity)))
            self.sales_table.setItem(i, 3, QTableWidgetItem(f'R{sale_price:.2f}')) # Renamed from Sale Price to Revenue
            self.sales_table.setItem(i, 4, QTableWidgetItem(f'R{cost_at_sale:.2f}')) # Display cost at sale
            self.sales_table.setItem(i, 5, QTableWidgetItem(sale_date))
            
            self.total_revenue += sale_price
            self.total_cogs += cost_at_sale

        self.sales_table.resizeColumnsToContents()
        self.calculate_and_display_metrics()

    def calculate_and_display_metrics(self):
        self.total_profit = self.total_revenue - self.total_cogs
        
        # We need a persistent way to track allocated profit, e.g., a simple config file or a dedicated DB table
        # For this example, let's just make it cumulative within this session, or zero on refresh for simplicity.
        # A more robust system would store remaining profit in the DB.
        # For now, let's assume all profit calculated is 'available' until allocated.
        
        # Read current allocation from a simple "config" table or file (implementing a simple one here)
        self.cursor.execute("SELECT SUM(amount) FROM profit_allocations WHERE type = 'Dividends'")
        dividends_paid = self.cursor.fetchone()[0] or 0.0
        self.cursor.execute("SELECT SUM(amount) FROM profit_allocations WHERE type = 'Stock Reinvestment'")
        stock_reinvested = self.cursor.fetchone()[0] or 0.0
        
        self.available_profit_for_allocation = self.total_profit - dividends_paid - stock_reinvested


        self.revenue_label.setText(f'R{self.total_revenue:.2f}')
        self.cogs_label.setText(f'R{self.total_cogs:.2f}')
        self.profit_label.setText(f'R{self.total_profit:.2f}')
        self.available_profit_label.setText(f'R{self.available_profit_for_allocation:.2f}')


    def _auto_refresh_data(self):
        """
        Refreshes both product and sales tables, and recalculates financial metrics.
        This is called by the QTimer.
        """
        self.refresh_product_table() # Products may have changed quantities due to sales
        self.refresh_sales_table()   # Sales history definitely changes due to sales

    def add_product_dialog(self):
        dialog = AddEditProductDialog(self, mode="add")
        if dialog.exec_() == QDialog.Accepted:
            new_product_name = dialog.name_edit.text()
            new_product_price = float(dialog.price_edit.text())
            self.refresh_product_table()
            self._auto_refresh_data() # Refresh all data after product changes
            QMessageBox.information(self, 'Product Added',
                                    f'New product added successfully: {new_product_name} (R{new_product_price:.2f}).')

    def edit_product(self):
        selected_rows = self.product_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a product to edit.")
            return

        row = selected_rows[0].row()
        product_code = self.product_table.item(row, 0).text()

        product_to_edit = next((p for p in self.products if p.code == product_code), None)
        if product_to_edit:
            dialog = AddEditProductDialog(self, product_to_edit, mode="edit")
            if dialog.exec_() == QDialog.Accepted:
                self.refresh_product_table()
                self._auto_refresh_data() # Refresh all data after product changes
                QMessageBox.information(self, 'Product Updated', 'Product details updated successfully.')
        else:
            QMessageBox.critical(self, "Error", "Selected product not found.")

    def delete_product(self):
        selected_rows = self.product_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a product to delete.")
            return

        row = selected_rows[0].row()
        product_code = self.product_table.item(row, 0).text()
        product_name = self.product_table.item(row, 1).text()

        reply = QMessageBox.question(self, 'Confirm Deletion',
                                    f'Are you sure you want to delete product "{product_name}" (Code: {product_code})? This action cannot be undone.',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute('DELETE FROM products WHERE code = ?', (product_code,))
                self.db.commit()
                self.refresh_product_table()
                self._auto_refresh_data() # Refresh all data after product deletion
                QMessageBox.information(self, 'Product Deleted', f'Product "{product_name}" deleted successfully.')
            except sqlite3.Error as e:
                QMessageBox.critical(self, 'Database Error', f'Error deleting product: {e}')

    def clear_sales_history(self):
        reply = QMessageBox.question(self, 'Clear Sales History',
                                    'Are you absolutely sure you want to CLEAR ALL SALES HISTORY? This action cannot be undone.',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute('DELETE FROM sales')
                self.db.commit()
                self.refresh_sales_table() # Refresh the table to show it's empty
                self._auto_refresh_data() # Recalculate metrics after clearing sales
                QMessageBox.information(self, 'History Cleared', 'All sales history has been successfully cleared.')
            except sqlite3.Error as e:
                QMessageBox.critical(self, 'Database Error', f'Error clearing sales history: {e}')

    def allocate_profit_dialog(self):
        if self.available_profit_for_allocation <= 0:
            QMessageBox.information(self, "No Profit to Allocate",
                                    "There is no positive profit available for allocation yet.")
            return

        dialog = ProfitAllocationDialog(self, self.available_profit_for_allocation)
        if dialog.exec_() == QDialog.Accepted:
            dividends = dialog.dividends_input.value()
            stock_reinvestment = dialog.stock_reinvestment_input.value()

            total_allocated = dividends + stock_reinvestment
            if total_allocated > self.available_profit_for_allocation:
                QMessageBox.warning(self, "Allocation Error",
                                    "Total allocated amount cannot exceed available profit.")
                return

            try:
                if dividends > 0:
                    self.cursor.execute(
                        "INSERT INTO profit_allocations (amount, type, date_allocated) VALUES (?, ?, ?)",
                        (dividends, "Dividends", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                if stock_reinvestment > 0:
                    self.cursor.execute(
                        "INSERT INTO profit_allocations (amount, type, date_allocated) VALUES (?, ?, ?)",
                        (stock_reinvestment, "Stock Reinvestment", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                self.db.commit()
                self._auto_refresh_data() # Recalculate metrics
                QMessageBox.information(self, "Profit Allocated",
                                        f"R{dividends:.2f} allocated to dividends.\n"
                                        f"R{stock_reinvestment:.2f} allocated to stock reinvestment.")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Database Error", f"Error allocating profit: {e}")

    def reset_profit_allocation(self):
        reply = QMessageBox.question(self, 'Reset Profit Allocation',
                                    'Are you sure you want to reset all profit allocation records? This action cannot be undone.',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute('DELETE FROM profit_allocations')
                self.db.commit()
                self._auto_refresh_data() # Recalculate metrics
                QMessageBox.information(self, 'Allocation Reset', 'All profit allocation records have been cleared.')
            except sqlite3.Error as e:
                QMessageBox.critical(self, 'Database Error', f'Error resetting allocation: {e}')


class AddEditProductDialog(QDialog):
    def __init__(self, parent=None, product=None, mode="add"):
        super().__init__(parent)
        self.db = parent.db
        self.cursor = self.db.cursor()
        self.product_to_edit = product
        self.mode = mode
        self.initUI()
        self.load_product_data()

    def initUI(self):
        self.setWindowTitle('Add/Edit Product')
        self.setGeometry(300, 200, 400, 400) # Slightly taller for new field
        self.setFont(QFont("Segoe UI", 11))

        form_layout = QFormLayout()
        self.setLayout(form_layout)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Unique product code (e.g., P001)")
        form_layout.addRow('Product Code:', self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Product name (e.g., Apple)")
        form_layout.addRow('Product Name:', self.name_edit)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Short description (optional)")
        form_layout.addRow('Description:', self.description_edit)

        self.price_edit = QLineEdit()
        self.price_edit.setValidator(QDoubleValidator(0.00, 999999.99, 2))
        self.price_edit.setPlaceholderText("Sale Price (e.g., 10.50)")
        form_layout.addRow('Sale Price (R):', self.price_edit)

        # NEW: Cost Price input
        self.cost_price_edit = QLineEdit()
        self.cost_price_edit.setValidator(QDoubleValidator(0.00, 999999.99, 2))
        self.cost_price_edit.setPlaceholderText("Cost Price (e.g., 6.00)")
        form_layout.addRow('Cost Price (R):', self.cost_price_edit)

        self.quantity_edit = QLineEdit()
        self.quantity_edit.setValidator(QIntValidator(0, 99999))
        self.quantity_edit.setPlaceholderText("Initial quantity (e.g., 100)")
        form_layout.addRow('Quantity:', self.quantity_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_input)
        button_box.rejected.connect(self.reject)
        form_layout.addRow(button_box)

        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QDialogButtonBox QPushButton {
                background-color: #28a745;
                color: #ffffff;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #218838;
            }
            QDialogButtonBox QPushButton#qt_cancelButton {
                background-color: #6c757d;
            }
            QDialogButtonBox QPushButton#qt_cancelButton:hover {
                background-color: #5a6268;
            }
        """)
        
        self.setWindowIcon(QIcon('icons/product_dialog.png'))

    def load_product_data(self):
        if self.product_to_edit:
            self.setWindowTitle('Edit Product')
            self.code_edit.setText(self.product_to_edit.code)
            self.code_edit.setReadOnly(True)
            self.name_edit.setText(self.product_to_edit.name)
            self.description_edit.setText(self.product_to_edit.description)
            self.price_edit.setText(str(self.product_to_edit.price))
            self.cost_price_edit.setText(str(self.product_to_edit.cost_price)) # Load cost price
            self.quantity_edit.setText(str(self.product_to_edit.quantity))

    def accept_input(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()
        description = self.description_edit.text().strip()
        price_text = self.price_edit.text().strip()
        cost_price_text = self.cost_price_edit.text().strip() # Get cost price
        quantity_text = self.quantity_edit.text().strip()

        if not (code and name and price_text and cost_price_text and quantity_text): # Check new field
            QMessageBox.warning(self, 'Missing Information', 'Please fill in all required fields (Code, Name, Sale Price, Cost Price, Quantity).')
            return

        try:
            price = float(price_text)
            cost_price = float(cost_price_text) # Convert cost price
            quantity = int(quantity_text)

            if price <= 0:
                QMessageBox.warning(self, 'Invalid Sale Price', 'Sale Price must be greater than zero.')
                return
            if cost_price < 0: # Cost can be 0, but not negative
                QMessageBox.warning(self, 'Invalid Cost Price', 'Cost Price cannot be negative.')
                return
            if quantity < 0:
                QMessageBox.warning(self, 'Invalid Quantity', 'Quantity cannot be negative.')
                return

            if self.product_to_edit:
                self.cursor.execute(
                    'UPDATE products SET name = ?, description = ?, price = ?, quantity = ?, cost_price = ? WHERE code = ?', # Update statement
                    (name, description, price, quantity, cost_price, code)
                )
            else:
                self.cursor.execute(
                    'INSERT INTO products (code, name, description, price, quantity, cost_price) VALUES (?, ?, ?, ?, ?, ?)', # Insert statement
                    (code, name, description, price, quantity, cost_price)
                )
            
            self.db.commit()
            self.accept()

        except ValueError:
            QMessageBox.warning(self, 'Invalid Input', 'Please enter valid numerical values for Sale Price, Cost Price, and Quantity.')
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, 'Duplicate Code', f'Product code "{code}" already exists. Please use a unique code.')
        except sqlite3.Error as e:
            QMessageBox.critical(self, 'Database Error', f'An unexpected database error occurred: {e}')

class ProfitAllocationDialog(QDialog):
    def __init__(self, parent=None, available_profit=0.0):
        super().__init__(parent)
        self.db = parent.db
        self.cursor = self.db.cursor()
        self.available_profit = available_profit
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Allocate Profit")
        self.setGeometry(400, 300, 450, 250)
        self.setFont(QFont("Segoe UI", 11))

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        info_label = QLabel(f"Available Profit to Allocate: <span style='font-weight:bold; color:#28a745;'>R{self.available_profit:.2f}</span>")
        info_label.setFont(QFont("Segoe UI", 11))
        main_layout.addWidget(info_label)

        form_layout = QFormLayout()

        self.dividends_input = QDoubleSpinBox()
        self.dividends_input.setSingleStep(100.00)
        self.dividends_input.setMinimum(0.00)
        self.dividends_input.setMaximum(self.available_profit)
        self.dividends_input.setPrefix("R")
        self.dividends_input.setValue(0.00)
        form_layout.addRow("Allocate to Dividends:", self.dividends_input)

        self.stock_reinvestment_input = QDoubleSpinBox()
        self.stock_reinvestment_input.setSingleStep(100.00)
        self.stock_reinvestment_input.setMinimum(0.00)
        self.stock_reinvestment_input.setMaximum(self.available_profit)
        self.stock_reinvestment_input.setPrefix("R")
        self.stock_reinvestment_input.setValue(0.00)
        form_layout.addRow("Allocate to Buying More Stock:", self.stock_reinvestment_input)

        main_layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.check_and_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { color: #333333; font-size: 11pt; }
            QDoubleSpinBox { padding: 8px; border: 1px solid #ced4da; border-radius: 4px; background-color: #ffffff; }
            QDialogButtonBox QPushButton {
                background-color: #007bff;
                color: #ffffff;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QDialogButtonBox QPushButton:hover { background-color: #0056b3; }
            QDialogButtonBox QPushButton#qt_cancelButton { background-color: #6c757d; }
            QDialogButtonBox QPushButton#qt_cancelButton:hover { background-color: #5a6268; }
        """)

    def check_and_accept(self):
        dividends = self.dividends_input.value()
        stock_reinvestment = self.stock_reinvestment_input.value()
        total_allocated = dividends + stock_reinvestment

        if total_allocated > self.available_profit:
            QMessageBox.warning(self, "Allocation Error",
                                f"Total allocated (R{total_allocated:.2f}) cannot exceed available profit (R{self.available_profit:.2f}).")
        else:
            self.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    conn = sqlite3.connect('pos.db')
    cursor = conn.cursor()
    # Initial setup for products table with cost_price
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
    # Initial setup for sales table with cost_at_sale
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
    # NEW: Table for tracking profit allocations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profit_allocations (
            allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            type TEXT NOT NULL, -- 'Dividends' or 'Stock Reinvestment'
            date_allocated TEXT NOT NULL
        )
    ''')

    # Add columns if they don't exist for existing databases (simple migration)
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN cost_price REAL NOT NULL DEFAULT 0.00")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        cursor.execute("ALTER TABLE sales ADD COLUMN cost_at_sale REAL NOT NULL DEFAULT 0.00")
    except sqlite3.OperationalError:
        pass # Column already exists
    conn.commit()

    # Add some sample products if the database is empty for initial run
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

    management_app = ManagementTool()
    management_app.show()
    sys.exit(app.exec_())