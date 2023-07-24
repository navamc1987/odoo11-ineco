-- View: public.query_stock_transaction_odoo

-- DROP VIEW public.query_stock_transaction_odoo;

CREATE OR REPLACE VIEW public.query_stock_transaction_odoo
 AS
 SELECT raw.id,
    raw.stkcod,
    raw.docdat,
    raw.price,
    raw.quantity,
    raw.docnum,
    raw.partner_id,
    raw.invoice_id
   FROM (
         SELECT ail.id,
            pp.default_code AS stkcod,
            ai.date_invoice AS docdat,
            ail.price_unit AS price,
                CASE
                    WHEN ai.type::text = ANY (ARRAY['out_invoice'::character varying::text, 'in_refund'::character varying::text]) THEN round((- ail.quantity) / pu.factor, 2)
                    ELSE round(ail.quantity / pu.factor, 2)
                END AS quantity,
                CASE
                    WHEN ai.type::text = ANY (ARRAY['out_invoice'::character varying::text, 'out_refund'::character varying::text]) THEN ai.number
                    ELSE
                    CASE
                        WHEN ai.type::text = 'in_refund'::text THEN ai.number
                        ELSE ai.reference
                    END
                END AS docnum,
            ai.partner_id,
            ai.id AS invoice_id
           FROM account_invoice_line ail
             JOIN account_invoice ai ON ai.id = ail.invoice_id
             JOIN product_product pp ON pp.id = ail.product_id
             JOIN product_uom pu ON pu.id = ail.uom_id
	         JOIN account_journal aj on aj.id = ai.journal_id
          WHERE ai.state not in ('cancel', 'draft') and aj.type in ('sale','purchase')
        UNION
	     -- Production Cost
         SELECT sm.id,
            pp.default_code AS stkcod,
            sp.date AS docdat,
            coalesce((select value_float from ir_property where name = 'standard_price' and res_id = 'product.product,'||pp.id),0.00) AS price,
                CASE
                    WHEN sl.usage::text = 'production'::text THEN - sm.product_qty
                    ELSE sm.product_qty
                END AS quantity,
            sp.origin AS docnum,
            NULL::integer AS partner_id,
            NULL::integer AS invoice_id
           FROM stock_picking sp
             LEFT JOIN stock_move sm ON sm.picking_id = sp.id
             LEFT JOIN stock_location sl ON sl.id = sm.location_dest_id
             LEFT JOIN stock_location sl2 ON sl2.id = sm.location_id
             JOIN product_product pp ON pp.id = sm.product_id
          WHERE sm.state::text = 'done'::text AND (sl.name::text = 'Production'::text OR sl2.name::text = 'Production'::text) AND sp.date >= '2019-01-01 00:00:00'::timestamp without time zone) raw
  ORDER BY raw.docdat, raw.docnum, raw.id;



