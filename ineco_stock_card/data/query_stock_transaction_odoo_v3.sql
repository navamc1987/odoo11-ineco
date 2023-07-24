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
   FROM ( SELECT express_stcrd_dbf.id,
            express_stcrd_dbf.stkcod,
            express_stcrd_dbf.docdat,
            express_stcrd_dbf.lunitpr AS price,
                CASE
                    WHEN express_stcrd_dbf.lotbal > 0::numeric THEN express_stcrd_dbf.lotbal
                    ELSE - express_stcrd_dbf.trnqty
                END AS quantity,
            express_stcrd_dbf.docnum,
            NULL::integer AS partner_id,
            NULL::integer AS invoice_id
           FROM express_stcrd_dbf
          WHERE express_stcrd_dbf.docdat < '2019-01-01'::date
        UNION
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
                        ELSE ai.supplier_invoice_number
                    END
                END AS docnum,
            ai.partner_id,
            ai.id AS invoice_id
           FROM account_invoice_line ail
             JOIN account_invoice ai ON ai.id = ail.invoice_id
             JOIN product_product pp ON pp.id = ail.product_id
             JOIN product_uom pu ON pu.id = ail.uos_id
          WHERE (ai.state::text <> ALL (ARRAY['draft'::character varying::text, 'cancel'::character varying::text])) AND ai.date_invoice >= '2019-01-01'::date AND (ai.journal_id <> ALL (ARRAY[49, 38, 6]))
        UNION
         SELECT sm.id,
            pp.default_code AS stkcod,
            sp.date AS docdat,
            COALESCE(( SELECT stock_production_lot.total_cost * 1.00
                   FROM stock_production_lot
                  WHERE stock_production_lot.id = sm.restrict_lot_id), 0.00)::double precision AS price,
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

ALTER TABLE public.query_stock_transaction_odoo
    OWNER TO opentkc;


