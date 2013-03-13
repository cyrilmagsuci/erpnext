# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes, unittest
from webnotes.utils import flt

class TestStockEntry(unittest.TestCase):
	def test_auto_material_request(self):
		webnotes.conn.sql("""delete from `tabMaterial Request Item`""")
		webnotes.conn.sql("""delete from `tabMaterial Request`""")

		st1 = webnotes.bean(copy=test_records[0])
		st1.insert()
		st1.submit()

		st2 = webnotes.bean(copy=test_records[1])
		st2.insert()
		st2.submit()
		
		mr_name = webnotes.conn.sql("""select parent from `tabMaterial Request Item`
			where item_code='_Test Item'""")
			
		self.assertTrue(mr_name)
		
	def atest_material_receipt_gl_entry(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()
		
		stock_in_hand_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_in_hand_account")
		
		self.check_stock_ledger_entries("Stock Entry", mr.doc.name, 
			[["_Test Item", "_Test Warehouse", 50.0]])
			
		self.check_gl_entries("Stock Entry", mr.doc.name, 
			sorted([
				[stock_in_hand_account, 5000.0, 0.0], 
				["Stock Adjustment - _TC", 0.0, 5000.0]
			])
		)
		
		mr.cancel()
		self.check_stock_ledger_entries("Stock Entry", mr.doc.name, 
			sorted([["_Test Item", "_Test Warehouse", 50.0], 
				["_Test Item", "_Test Warehouse", -50.0]]))
			
		self.check_gl_entries("Stock Entry", mr.doc.name, 
			sorted([
				[stock_in_hand_account, 5000.0, 0.0], 
				["Stock Adjustment - _TC", 0.0, 5000.0],
				[stock_in_hand_account, 0.0, 5000.0], 
				["Stock Adjustment - _TC", 5000.0, 0.0]
			])
		)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)

	def atest_material_issue_gl_entry(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()
		
		mi = webnotes.bean(copy=test_records[1])
		mi.insert()
		mi.submit()
		
		stock_in_hand_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_in_hand_account")
		
		self.check_stock_ledger_entries("Stock Entry", mi.doc.name, 
			[["_Test Item", "_Test Warehouse", -40.0]])
			
		self.check_gl_entries("Stock Entry", mi.doc.name, 
			sorted([
				[stock_in_hand_account, 0.0, 4000.0], 
				["Stock Adjustment - _TC", 4000.0, 0.0]
			])
		)
		
		mi.cancel()
		
		self.check_stock_ledger_entries("Stock Entry", mi.doc.name, 
			sorted([["_Test Item", "_Test Warehouse", -40.0], 
				["_Test Item", "_Test Warehouse", 40.0]]))
			
		self.check_gl_entries("Stock Entry", mi.doc.name, 
			sorted([
				[stock_in_hand_account, 0.0, 4000.0], 
				["Stock Adjustment - _TC", 4000.0, 0.0],
				[stock_in_hand_account, 4000.0, 0.0], 
				["Stock Adjustment - _TC", 0.0, 4000.0],
			])
		)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		
	def test_material_transfer_gl_entry(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)

		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()

		mtn = webnotes.bean(copy=test_records[2])
		mtn.insert()
		mtn.submit()

		self.check_stock_ledger_entries("Stock Entry", mtn.doc.name, 
			[["_Test Item", "_Test Warehouse", -45.0], ["_Test Item", "_Test Warehouse 1", 45.0]])

		# no gl entry
		gl_entries = webnotes.conn.sql("""select * from `tabGL Entry` 
			where voucher_type = 'Stock Entry' and voucher_no=%s""", mtn.doc.name)
		self.assertFalse(gl_entries)
		
		mtn.cancel()
		self.check_stock_ledger_entries("Stock Entry", mtn.doc.name, 
			sorted([["_Test Item", "_Test Warehouse", 45.0], 
				["_Test Item", "_Test Warehouse 1", -45.0],
				["_Test Item", "_Test Warehouse", -45.0], 
				["_Test Item", "_Test Warehouse 1", 45.0]]))

		# no gl entry
		gl_entries = webnotes.conn.sql("""select * from `tabGL Entry` 
			where voucher_type = 'Stock Entry' and voucher_no=%s""", mtn.doc.name)
		self.assertFalse(gl_entries)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
	
	def check_stock_ledger_entries(self, voucher_type, voucher_no, expected_sle):
		# check stock ledger entries
		sle = webnotes.conn.sql("""select * from `tabStock Ledger Entry` where voucher_type = %s 
			and voucher_no = %s order by item_code, warehouse, actual_qty""", 
			(voucher_type, voucher_no), as_dict=1)
		self.assertTrue(sle)
		
		for i, sle in enumerate(sle):
			self.assertEquals(expected_sle[i][0], sle.item_code)
			self.assertEquals(expected_sle[i][1], sle.warehouse)
			self.assertEquals(expected_sle[i][2], sle.actual_qty)
		
	def acheck_gl_entries(self, voucher_type, voucher_no, expected_gl_entries):
		# check gl entries
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s 
			order by account asc, debit asc""", (voucher_type, voucher_no), as_dict=1)
		self.assertTrue(gl_entries)
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle.account)
			self.assertEquals(expected_gl_entries[i][1], gle.debit)
			self.assertEquals(expected_gl_entries[i][2], gle.credit)
	
	def _clear_stock(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.conn.sql("""delete from `tabBin`""")
	
	def _insert_material_receipt(self):
		self._clear_stock()
		material_receipt = webnotes.bean(copy=test_records[0])
		material_receipt.insert()
		material_receipt.submit()
		
	def _get_actual_qty(self):
		return flt(webnotes.conn.get_value("Bin", {"item_code": "_Test Item", 
			"warehouse": "_Test Warehouse"}, "actual_qty"))
			
	def _test_sales_invoice_return(self, item_code, delivered_qty, returned_qty):
		from stock.doctype.stock_entry.stock_entry import NotUpdateStockError
		
		from accounts.doctype.sales_invoice.test_sales_invoice \
			import test_records as sales_invoice_test_records
		
		# invalid sales invoice as update stock not checked
		si = webnotes.bean(copy=sales_invoice_test_records[1])
		si.insert()
		si.submit()
		
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.sales_invoice_no = si.doc.name
		se.doclist[1].qty = returned_qty
		se.doclist[1].transfer_qty = returned_qty
		self.assertRaises(NotUpdateStockError, se.insert)
		
		self._insert_material_receipt()
		
		# check currency available qty in bin
		actual_qty_0 = self._get_actual_qty()
		
		# insert a pos invoice with update stock
		si = webnotes.bean(copy=sales_invoice_test_records[1])
		si.doc.is_pos = si.doc.update_stock = 1
		si.doclist[1].warehouse = "_Test Warehouse"
		si.doclist[1].item_code = item_code
		si.insert()
		si.submit()
		
		# check available bin qty after invoice submission
		actual_qty_1 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)
		
		# check if item is validated
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.sales_invoice_no = si.doc.name
		se.doc.posting_date = "2013-03-10"
		se.doclist[1].item_code = "_Test Item Home Desktop 200"
		se.doclist[1].qty = returned_qty
		se.doclist[1].transfer_qty = returned_qty
		
		# check if stock entry gets submitted
		self.assertRaises(webnotes.DoesNotExistError, se.insert)
		
		# try again
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.posting_date = "2013-03-10"
		se.doc.sales_invoice_no = si.doc.name
		se.doclist[1].qty = returned_qty
		se.doclist[1].transfer_qty = returned_qty
		# in both cases item code remains _Test Item when returning
		se.insert()
		
		se.submit()
		
		# check if available qty is increased
		actual_qty_2 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)
	
	def test_sales_invoice_return_of_non_packing_item(self):
		self._test_sales_invoice_return("_Test Item", 5, 2)
			
	def test_sales_invoice_return_of_packing_item(self):
		self._test_sales_invoice_return("_Test Sales BOM Item", 25, 20)
		
	def _test_delivery_note_return(self, item_code, delivered_qty, returned_qty):
		self._insert_material_receipt()
		
		actual_qty_0 = self._get_actual_qty()
		
		# insert and submit delivery note
		from stock.doctype.delivery_note.test_delivery_note \
			import test_records as delivery_note_test_records
		dn = webnotes.bean(copy=delivery_note_test_records[0])
		dn.doclist[1].item_code = item_code
		dn.insert()
		dn.submit()
		
		actual_qty_1 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)
		
		# insert and submit stock entry for sales return
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.delivery_note_no = dn.doc.name
		se.doc.posting_date = "2013-03-01"
		se.doclist[1].qty = se.doclist[1].transfer_qty = returned_qty
		
		se.insert()
		se.submit()
		
		actual_qty_2 = self._get_actual_qty()
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)
		
	def test_delivery_note_return_of_non_packing_item(self):
		self._test_delivery_note_return("_Test Item", 5, 2)
		
	def test_delivery_note_return_of_packing_item(self):
		self._test_delivery_note_return("_Test Sales BOM Item", 25, 20)
		
	def test_purchase_receipt_return(self):
		self._clear_stock()
		
		actual_qty_0 = self._get_actual_qty()
		
		from stock.doctype.purchase_receipt.test_purchase_receipt \
			import test_records as purchase_receipt_test_records
		
		# submit purchase receipt
		pr = webnotes.bean(copy=purchase_receipt_test_records[0])
		pr.insert()
		pr.submit()
		
		actual_qty_1 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_0 + 10, actual_qty_1)
		
		# submit purchase return
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Purchase Return"
		se.doc.purchase_receipt_no = pr.doc.name
		se.doc.posting_date = "2013-03-01"
		se.doclist[1].qty = se.doclist[1].transfer_qty = 5
		se.doclist[1].s_warehouse = "_Test Warehouse"
		se.insert()
		se.submit()
		
		actual_qty_2 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_1 - 5, actual_qty_2)
		

test_records = [
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:14:24", 
			"purpose": "Material Receipt",
			"fiscal_year": "_Test Fiscal Year 2013", 
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 50.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 50.0, 
			"uom": "_Test UOM",
			"t_warehouse": "_Test Warehouse",
		}, 
	],
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:15", 
			"purpose": "Material Issue",
			"fiscal_year": "_Test Fiscal Year 2013", 
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 40.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 40.0, 
			"uom": "_Test UOM",
			"s_warehouse": "_Test Warehouse",
		}, 
	],
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:14:24", 
			"purpose": "Material Transfer",
			"fiscal_year": "_Test Fiscal Year 2013", 
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 45.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 45.0, 
			"uom": "_Test UOM",
			"s_warehouse": "_Test Warehouse",
			"t_warehouse": "_Test Warehouse 1",
		}
	]
]