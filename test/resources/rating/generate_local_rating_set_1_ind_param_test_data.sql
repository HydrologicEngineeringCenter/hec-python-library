set serveroutput on
declare
   l_rating_id  cwms_v_rating.rating_id%type;
   l_elevations cwms_t_double_tab;
   l_storages   cwms_t_double_tab;
   l_times      cwms_t_date_table;
begin
   l_rating_id := 'KEYS.Elev;Stor.Linear.Production';
   l_elevations := cwms_t_double_tab(660, 692.3, 722.1, 756, 770.5);
   l_times := cwms_t_date_table();
   l_times.extend(l_elevations.count);
   
   for year in 2009..2021 loop
      for i in 1..l_times.count loop
         l_times(i) := to_date(year||'-01-01', 'yyyy-mm-dd'); 
      end loop;
      l_storages := cwms_rating.rate_f(
         p_rating_spec => l_rating_id,
         p_values      => cwms_t_double_tab_tab(l_elevations),
         p_units       => cwms_t_str_tab('ft', 'ac-ft'),
         p_value_times => l_times,
         p_time_zone   => 'UTC');
      for i in 1..l_elevations.count loop   
         dbms_output.put_line(
            to_char(cast(l_times(i) as timestamp), 'yyyy-mm-dd"T"hh24:mi:sstzr')
            ||chr(9)||round(to_number(l_elevations(i)),5)
            ||chr(9)||round(to_number(l_storages(i)),5));
      end loop;      
   end loop;
end;
/

