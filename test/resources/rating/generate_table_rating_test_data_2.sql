set serveroutput on
declare
   l_rating_id  cwms_v_rating.rating_id%type;
   l_elevations cwms_t_double_tab;
   l_storages   cwms_t_double_tab;
begin
   l_rating_id := 'KEYS.Elev;Stor.Linear.Production';
   l_elevations := cwms_t_double_tab(660, 692.3, 722.1, 756, 770.5);
   
   l_storages := cwms_rating.rate_f(
      l_rating_id,
      cwms_t_double_tab_tab(l_elevations),
      cwms_t_str_tab('ft', 'ac-ft'),
      p_rating_time => date '2012-10-31');
   for i in 1..l_elevations.count loop   
      dbms_output.put_line(
         round(to_number(l_elevations(i)),5)
         ||chr(9)||round(to_number(l_storages(i)),5));
   end loop;      
end;
/

