# coding-repo
My first repository with the point of sales program in python.
 POS System A comprehensive Point of Sale system built with Python and PyQt5, featuring a modern GUI interface, SQLite database backend, and real-time inventory management.

🚀 Features POS Client Intuitive Sales Interface - Product selection with real-time stock validation

Shopping Cart Management - Add, remove, and modify items before checkout

Receipt Generation - Professional receipts with VAT calculation and formatting

Real-time Updates - Automatic detection of new products and stock changes

Cashier Management - User identification for transaction tracking

Management Tool Product Management - Complete CRUD operations for inventory items

Sales Analytics - Comprehensive sales history and reporting

Financial Tracking - Revenue, COGS, and profit calculations

Profit Allocation - Distribute profits to dividends and stock reinvestment

Auto-refresh - Real-time data synchronization

📋 Prerequisites Python 3.7 or higher

PyQt5 library

🛠 Installation Clone the repository

bash git clone https://github.com/NYWMTH003/coding-repo.git cd pos-system Install required dependencies

bash pip install PyQt5 Run the application

For sales operations (Cashiers):

bash python pos_client.py For administrative tasks (Managers):

bash python management_tool.py 🗃 Database Schema The system uses SQLite with the following tables:

Products Table code (TEXT PRIMARY KEY) - Unique product identifier

name (TEXT) - Product name

description (TEXT) - Product description

price (REAL) - Selling price

quantity (INTEGER) - Stock quantity

cost_price (REAL) - Purchase cost

Sales Table sale_id (INTEGER PRIMARY KEY AUTOINCREMENT)

product_code (TEXT) - Reference to product

quantity (INTEGER) - Quantity sold

sale_price (REAL) - Total sale amount

cost_at_sale (REAL) - Cost at time of sale

sale_date (TEXT) - Transaction timestamp

Profit Allocations Table allocation_id (INTEGER PRIMARY KEY AUTOINCREMENT)

amount (REAL) - Allocation amount

type (TEXT) - 'Dividends' or 'Stock Reinvestment'

date_allocated (TEXT) - Allocation timestamp

🎯 Usage For Cashiers Launch pos_client.py

Select products from the dropdown menu

Set quantities (validated against available stock)

Add items to cart

Click "View Cart" to review and process sale

Print receipt after successful transaction

For Managers Launch management_tool.py

Product Management: Add, edit, or remove products

Sales Monitoring: View complete transaction history

Financial Overview: Track revenue, costs, and profits

Profit Allocation: Distribute profits to different categories

🔧 Configuration Customizing Business Information Edit the display_sale_slip method in pos_client.py to update:

Company name and slogan

Store location

VAT registration number

Contact information

Promotional messages

Modifying VAT Rate Update the VAT rate in pos_client.py:

python vat_rate = 0.15 # Change to your local VAT percentage Icons (Optional) Create an icons folder with the following files for enhanced UI:

add_to_cart.png, view_cart.png, print.png, back.png

add_product.png, edit.png, delete.png, clear.png

checkout.png, management.png, clear_history.png

allocate_profit.png, reset.png, product_dialog.png

remove_item.png

🏗 Project Structure text pos-system/ ├── pos_client.py # Main POS interface ├── cart_dialog.py # Cart management component ├── management_tool.py # Administrative interface ├── pos.db # SQLite database (auto-generated) ├── icons/ # UI icons (optional) │ ├── add_to_cart.png │ ├── view_cart.png │ └── ... └── README.md 🔄 Auto-Initialization On first run, the system automatically:

Creates the SQLite database (pos.db)

Sets up all required tables with proper schema

Adds sample products if the database is empty

Handles schema migrations for existing databases

🐛 Troubleshooting Common Issues Database Errors

Ensure write permissions in the application directory

Check if pos.db is not locked by another process

Missing Dependencies

bash pip install --upgrade PyQt5 UI Not Loading

Verify Python version compatibility

Check console for error messages

Icons Not Displaying

Icons are optional - functionality works without them

Ensure icon files are in the icons folder

🤝 Contributing Fork the repository

Create a feature branch (git checkout -b feature/amazing-feature)

Commit your changes (git commit -m 'Add amazing feature')

Push to the branch (git push origin feature/amazing-feature)

Open a Pull Request

📝 License This project is licensed under the MIT License - see the LICENSE file for details.

🆓 Icons Icons are optional for functionality. The application will work without them, using text labels instead.

Note: This system is designed for single-store operations with local database storage. For multi-store or cloud-based requirements, consider additional development for database synchronization and user management.
