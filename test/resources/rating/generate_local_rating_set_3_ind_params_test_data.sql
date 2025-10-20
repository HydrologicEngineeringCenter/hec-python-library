set serveroutput on
declare
   l_rating_id  cwms_v_rating.rating_id%type;
   l_times      cwms_t_date_table;
   l_counts     cwms_t_double_tab;
   l_openings   cwms_t_double_tab;
   l_elevations cwms_t_double_tab;
   l_flow       cwms_t_double_tab;
begin
   l_rating_id := 'COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production';
   l_times := cwms_t_date_table(date '2012-04-26', date '2012-04-27', date '2012-04-28');
   l_counts := cwms_t_double_tab(1, 2);
   l_openings := cwms_t_double_tab(0, 1.2, 3, 6.7, 12.1);
   l_elevations := cwms_t_double_tab(1223, 1250.3, 1281.7, 1300);
   
   for i in 1..l_times.count loop
      for j in 1..l_counts.count loop
         for k in 1..l_openings.count loop
            for m in 1..l_elevations.count loop
               l_flow := cwms_rating.rate_f(
                  p_rating_spec => l_rating_id,
                  p_values      => cwms_t_double_tab_tab(cwms_t_double_tab(l_counts(j)), cwms_t_double_tab(l_openings(k)), cwms_t_double_tab(l_elevations(m))),
                  p_units       => cwms_t_str_tab('unit', 'ft', 'ft', 'cfs'),
                  p_value_times => cwms_t_date_table(l_times(i)),
                  p_time_zone   => 'UTC');
               dbms_output.put_line(
                  to_char(cast(l_times(i) as timestamp), 'yyyy-mm-dd"T"hh24:mi:sstzr')
                  ||chr(9)||round(to_number(l_counts(j)), 5)
                  ||chr(9)||round(to_number(l_openings(k)), 5)
                  ||chr(9)||round(to_number(l_elevations(m)), 5)
                  ||chr(9)||round(to_number(l_flow(1)),5));
            end loop;
         end loop;
      end loop;
   end loop;
end;
/