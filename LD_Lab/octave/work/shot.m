function shot(n)
  % asks the external capture script to photograph the Octave windows and waits for it
  drawnow;
  pause(1.0);
  d = getenv('SHOTDIR');
  f = sprintf('%s/req_%02d.txt', d, n);
  fid = fopen(f, 'w'); fprintf(fid, '1'); fclose(fid);
  ok = sprintf('%s/ok_%02d.txt', d, n);
  t0 = tic;
  while !exist(ok, 'file') && toc(t0) < 30
    pause(0.2);
  end
end
