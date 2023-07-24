CREATE or replace FUNCTION get_pl_value(date_start text, date_end text, code text)
 RETURNS float AS $amount$
 DECLARE amount float;
BEGIN
	select
	  sum(worksheet.pl_credit - worksheet.pl_debit) as balance into amount
	from
	(
	select
	  aa.id,
	  aa.code,
	  aa.name,
	COALESCE(
	  case when sum(aml.debit) - sum(aml.credit) >= 0 then sum(aml.debit) - sum(aml.credit) else 0 end ,0.0) as debit,
	COALESCE(
	  case when sum(aml.debit) - sum(aml.credit) < 0 then sum(aml.credit) - sum(aml.debit) else 0 end,0.0) as credit,
	COALESCE(
	  case when aa.inventory_ok or left(aa.code,1) in ('4','5') then
			 case when sum(aml.debit) - sum(aml.credit) >= 0 then sum(aml.debit) - sum(aml.credit) else 0 end
		   else 0 end,0.0) as pl_debit,
	COALESCE(
	  case when left(aa.code,1) in ('4','5') then
			 case when sum(aml.debit) - sum(aml.credit) < 0 then sum(aml.credit) - sum(aml.debit) else 0 end
		   else 0 end ,0.0)as pl_credit,
	COALESCE(
	  case when aa.inventory_ok is null and left(aa.code,1) in ('1','2','3') then
			 case when sum(aml.debit) - sum(aml.credit) >= 0 then sum(aml.debit) - sum(aml.credit) else 0 end
		   else 0 end,0.0) as bs_debit,
	COALESCE(
	  case when left(aa.code,1) in ('1','2','3') then
			 case when sum(aml.debit) - sum(aml.credit) < 0 then sum(aml.credit) - sum(aml.debit) else 0 end
		   else 0 end,0.0) as bs_credit
	from account_move_line	as aml
	join account_account as aa 	on aa.id = aml.account_id
	join account_move am on am.id = aml.move_id
	join account_journal aj on aj.id = am.journal_id
	where aml.state ='valid'
	   and aml.date >= to_date($1, 'yyyy-MM-DD')
	   and aml.date <= to_date($2, 'yyyy-MM-DD') and extract(year from aml.date) = extract(year from  to_date($2, 'yyyy-MM-DD'))
	  and aa.active = true
	  and (aj.hide_account_report is null or aj.hide_account_report = false)
	group by aa.id, aa.code,aa.name,aa.inventory_ok
	union
	(select
	  account_account.id,
	  account_account.code||'*',
	  account_account.name || ' (Ending)' as name,
	  0.0 as debit,
	  0.0 as credit,
	  0.0 as pl_debit,
	COALESCE(
	  (select (select sum(balance_value) from ineco_stock_card_product
	   where stock_period_id = ineco_stock_card.id) as ending_values from ineco_stock_card
		where date_to >= to_date($1, 'yyyy-MM-dd') and date_from <= to_date($2, 'yyyy-MM-DD')
	and date_to <> to_date(to_char(to_date($1, 'yyyy-MM-dd'), 'YYYY') || '-01-01', 'yyyy-MM-dd')
	limit 1),0.0) as pl_credit,
	COALESCE(
	  (select (select sum(balance_value) from ineco_stock_card_product
	   where stock_period_id = ineco_stock_card.id) as ending_values from ineco_stock_card
		where date_to >= to_date($1, 'yyyy-MM-dd') and date_from <= to_date($2, 'yyyy-MM-DD')
	and date_to <> to_date(to_char(to_date($1, 'yyyy-MM-dd'), 'YYYY') || '-01-01', 'yyyy-MM-dd')
	 limit 1),0.0) as bs_debit,
	  0.0 bs_credit
	from account_account
	where inventory_ok = true
	limit 1)
	order by code) worksheet
	left join account_account aa on aa.id = worksheet.id
	left join account_account aa2 on aa2.id = aa.parent_id	
	left join account_account aa3 on aa3.id = aa2.parent_id
	where 
	  (pl_debit > 0 or pl_credit > 0) and aa2.code = $3
	group by
	  aa2.code, aa2.name, aa2.parent_id;
	return amount;
END; $amount$
LANGUAGE PLPGSQL;
--select get_pl_value('2019-01-01','2019-02-28','4100-00') ;