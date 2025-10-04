# cart_dialog.py
import sys
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sqlite3
from datetime import datetime

class CartDialog(QWidget):  # Changed from QDialog to QWidget
    def __init__(self, db_connection, cart_data, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.cursor = self.db.cursor()
        self.cart = cart_data
        self.parent_pos_client = parent
        self.processed_cart_items = []
        self.final_total_amount = 0.0

        self.initUI()
        self.update_cart_display()

    def initUI(self):
        # Remove window title and geometry since we're embedding
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(['Code', 'Name', 'Quantity', 'Price (R)', 'Subtotal (R)'])
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.horizontalHeader().setStretchLastSection(True)
        self.cart_table.horizontalHeader().setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.cart_table.setFont(QFont("Segoe UI", 10))
        main_layout.addWidget(self.cart_table)

        total_layout = QHBoxLayout()
        total_layout.addStretch()
        total_label = QLabel('Total:')
        total_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        total_layout.addWidget(total_label)
        self.total_amount_label = QLabel('R0.00')
        self.total_amount_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.total_amount_label.setStyleSheet("color: #00698f;")
        total_layout.addWidget(self.total_amount_label)
        main_layout.addLayout(total_layout)

        button_layout = QHBoxLayout()

        remove_item_button = QPushButton('Remove Selected Item')
        remove_item_button.setIcon(QIcon('icons/remove_item.png'))
        remove_item_button.clicked.connect(self.remove_selected_item)
        button_layout.addWidget(remove_item_button)

        clear_cart_button = QPushButton('Clear All Items')
        clear_cart_button.setIcon(QIcon('icons/clear.png'))
        clear_cart_button.setStyleSheet("background-color: #dc3545;")
        clear_cart_button.clicked.connect(self.clear_cart)
        button_layout.addWidget(clear_cart_button)

        checkout_button = QPushButton('Process Sale')
        checkout_button.setIcon(QIcon('icons/checkout.png'))
        checkout_button.setStyleSheet("background-color: #28a745;")
        checkout_button.clicked.connect(self.process_sale)
        button_layout.addWidget(checkout_button)

        main_layout.addLayout(button_layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #e0e6ed;
                font-family: 'Segoe UI', sans-serif;
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
            QPushButton[text="Clear All Items"] {
                background-color: #dc3545;
            }
            QPushButton[text="Clear All Items"]:hover {
                background-color: #c82333;
            }
            QPushButton[text="Process Sale"] {
                background-color: #28a745;
            }
            QPushButton[text="Process Sale"]:hover {
                background-color: #218838;
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

    def update_cart_display(self):
        self.cart_table.setRowCount(len(self.cart))
        total_amount = 0.0
        for i, item in enumerate(self.cart):
            subtotal = item['quantity'] * item['price']
            self.cart_table.setItem(i, 0, QTableWidgetItem(item['product_code']))
            self.cart_table.setItem(i, 1, QTableWidgetItem(item['product_name']))
            self.cart_table.setItem(i, 2, QTableWidgetItem(str(item['quantity'])))
            self.cart_table.setItem(i, 3, QTableWidgetItem(f'{item["price"]:.2f}'))
            self.cart_table.setItem(i, 4, QTableWidgetItem(f'{subtotal:.2f}'))
            total_amount += subtotal
        
        self.total_amount_label.setText(f'R{total_amount:.2f}')
        self.final_total_amount = total_amount
        self.cart_table.resizeColumnsToContents()

    def remove_selected_item(self):
        selected_rows = self.cart_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select an item to remove from the cart.")
            return

        row_index = selected_rows[0].row()
        item_name = self.cart_table.item(row_index, 1).text()

        reply = QMessageBox.question(self, 'Remove Item',
                                    f'Are you sure you want to remove "{item_name}" from the cart?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            del self.cart[row_index]
            self.update_cart_display()
            QMessageBox.information(self, 'Item Removed', f'"{item_name}" removed from cart.')

    def clear_cart(self):
        if self.cart:
            reply = QMessageBox.question(self, 'Clear Cart', 'Are you sure you want to clear the entire cart?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.cart.clear()
                self.update_cart_display()
                QMessageBox.information(self, 'Cart Cleared', 'Shopping cart has been cleared.')
        else:
            QMessageBox.information(self, 'Cart Empty', 'The shopping cart is already empty.')

    def process_sale(self):
        if not self.cart:
            QMessageBox.warning(self, 'Empty Cart', 'The cart is empty. Please add items before processing a sale.')
            return

        total_amount_str = self.total_amount_label.text()
        reply = QMessageBox.question(self, 'Confirm Sale',
                                     f'Confirm sale for a total of {total_amount_str}?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.db.isolation_level = None
                self.cursor.execute('BEGIN TRANSACTION')

                self.processed_cart_items = list(self.cart)

                for item in self.cart:
                    product_code = item['product_code']
                    quantity_sold = item['quantity']
                    sale_price_total = item['price'] * quantity_sold
                    cost_at_sale_total = item['cost_price'] * quantity_sold

                    self.cursor.execute(
                        'INSERT INTO sales (product_code, quantity, sale_price, cost_at_sale, sale_date) VALUES (?, ?, ?, ?, ?)',
                        (product_code, quantity_sold, sale_price_total, cost_at_sale_total, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                    
                    self.cursor.execute(
                        'UPDATE products SET quantity = quantity - ? WHERE code = ?',
                        (quantity_sold, product_code)
                    )
                
                self.db.commit()
                self.cart.clear()
                self.update_cart_display()
                
                if self.parent_pos_client:
                    self.parent_pos_client.products = self.parent_pos_client.load_products()
                    self.parent_pos_client.update_product_combo()
                    # Call the new method to handle the sale completion
                    self.parent_pos_client.on_sale_processed(self.processed_cart_items, self.final_total_amount)

            except sqlite3.Error as e:
                self.db.rollback()
                QMessageBox.critical(self, 'Database Error', f'Error processing sale: {e}')
            finally:
                self.db.isolation_level = ''

    def get_processed_sale_details(self):
        return self.processed_cart_items, self.final_total_amount