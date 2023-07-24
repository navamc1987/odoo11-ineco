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
   FROM ( SELECT min(ail.id) AS id,
            pp.default_code AS stkcod,
            ai.date_invoice AS docdat,
            round(sum(ail.price_subtotal) / sum(ail.quantity), 4) AS price,
                CASE
                    WHEN ai.type::text = ANY (ARRAY['out_invoice'::character varying::text, 'in_refund'::character varying::text]) THEN round((- sum(ail.quantity)) / 1::numeric, 2)
                    ELSE round(sum(ail.quantity) / 1::numeric, 2)
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
             LEFT JOIN product_uom pu ON pu.id = ail.uom_id
             JOIN account_journal aj ON aj.id = ai.journal_id
          WHERE (ai.state::text <> ALL (ARRAY['cancel'::character varying::text, 'draft'::character varying::text])) AND (aj.type::text = ANY (ARRAY['sale'::character varying::text, 'purchase'::character varying::text]))
          GROUP BY pp.default_code, ai.date_invoice, ai.type, ai.number, ai.reference, ai.partner_id, ai.id
        UNION
         SELECT sm.id,
            pp.default_code AS stkcod,
            sp.scheduled_date AS docdat,
            COALESCE(( SELECT ir_property.value_float
                   FROM ir_property
                  WHERE ir_property.name::text = 'standard_price'::text AND ir_property.res_id::text = ('product.product,'::text || pp.id)), 0.00::double precision) AS price,
                CASE
                    WHEN sl.usage::text = 'production'::text THEN - sm.product_qty
                    ELSE sm.product_qty
                END AS quantity,
                CASE
                    WHEN sp.origin IS NOT NULL THEN sp.origin
                    ELSE sp.name
                END AS docnum,
            NULL::integer AS partner_id,
            NULL::integer AS invoice_id
           FROM stock_picking sp
             LEFT JOIN stock_move sm ON sm.picking_id = sp.id
             LEFT JOIN stock_location sl ON sl.id = sm.location_dest_id
             LEFT JOIN stock_location sl2 ON sl2.id = sm.location_id
             JOIN product_product pp ON pp.id = sm.product_id
          WHERE sm.state::text = 'done'::text AND (sl.name::text = 'Production'::text OR sl2.name::text = 'Production'::text)
        UNION
         SELECT sm.id,
            pp.default_code AS stkcod,
                CASE
                    WHEN sm.inventory_id IS NOT NULL THEN sm.date::date
                    ELSE ( SELECT min(sp.scheduled_date)::date AS min
                       FROM stock_picking sp
                      WHERE sp.id = sm.picking_id)
                END AS docdat,
             (select coalesce(bf_cost, 0.0000) from ineco_stock_card_product
			 where product_id = pp.id and stock_date_to <= sm.date order by stock_date_to desc limit 1) as price,
		 --round(COALESCE(( SELECT ir_property.value_float
         --          FROM ir_property
         --         WHERE ir_property.name::text = 'standard_price'::text AND ir_property.res_id::text = ('product.product,'::text || pp.id)), 0.00::double precision)::numeric, 4) AS price,

            round(
                CASE
                    WHEN sl.usage::text = 'inventory'::text THEN - sm.product_qty
                    ELSE sm.product_qty
                END, 3) AS quantity,
            ( SELECT stock_picking.name
                   FROM stock_picking
                  WHERE stock_picking.id = sm.picking_id) AS docnum,
            NULL::integer AS partner_id,
            NULL::integer AS invoice_id
           FROM stock_move sm
             LEFT JOIN stock_location sl ON sl.id = sm.location_dest_id
             LEFT JOIN stock_location sl2 ON sl2.id = sm.location_id
             JOIN product_product pp ON pp.id = sm.product_id
          WHERE sm.state::text = 'done'::text AND (sl.usage::text = 'inventory'::text OR sl2.usage::text = 'inventory'::text)) raw
  ORDER BY raw.docdat, raw.docnum, raw.id;


