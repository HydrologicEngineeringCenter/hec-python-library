declare
   l_rating_id  cwms_v_rating.rating_id%type;
   l_counts     cwms_t_double_tab;
   l_openings   cwms_t_double_tab;
   l_elevations cwms_t_double_tab;
   l_flow       cwms_t_double_tab;
begin
   l_rating_id := 'COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production';
   l_counts := cwms_t_double_tab(1, 2);
   l_openings := cwms_t_double_tab(0, 1.5, 3, 6.5, 12.5);
   l_elevations := cwms_t_double_tab(1223, 1250.5, 1281.2, 1300);
   
   for i in 1..l_counts.count loop
      for j in 1..l_openings.count loop
         for k in 1..l_elevations.count loop
            l_flow := cwms_rating.rate_f(
               l_rating_id,
               cwms_t_double_tab_tab(cwms_t_double_tab(l_counts(i)), cwms_t_double_tab(l_openings(j)), cwms_t_double_tab(l_elevations(k))),
               cwms_t_str_tab('unit', 'ft', 'ft', 'cfs'));
            dbms_output.put_line(
               to_number(l_counts(i))
               ||chr(9)||to_number(l_openings(j))
               ||chr(9)||to_number(l_elevations(k))
               ||chr(9)||round(to_number(l_flow(1)),5));
         end loop;
      end loop;
   end loop;
end;
/