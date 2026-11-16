% Step-by-step run of the lens distortion correction (book of H. Farid, section 9.6) on a new photo.
% Every cmd(...) prints the command as in the Command Window and runs it; shot(N) takes the screenshots.
more off;
format short;
n = 0;
function n = nextshot(n)
  n = n + 1;
  shot(n);
end

try, system('mode con: cols=170 lines=48'); catch, end
clc;
cmd('version');
cmd('pwd');
cmd('ls');
n = nextshot(n);                                   % 1: program, version, folder

% ---------------------------------------------------------------- PART 1: the algorithm step by step
cmd('im = double( imread( ''monkey.png'' ) );');
cmd('[ydim,xdim,zdim] = size( im )');
cmd('figure(1); imshow( uint8( im ) ); title( ''Step 1: original image (imread)'' );');
set(1, 'Position', [60 60 760 560]);
n = nextshot(n);                                   % 2: read the image

cmd('impad = zeros( ydim+100, xdim+100, zdim );');
cmd('impad(51:ydim+50,51:xdim+50,:) = im;');
cmd('size( impad )');
cmd('imshow( uint8( impad ) ); title( ''Step 2: zero padding, 50 px on every side'' );');
n = nextshot(n);                                   % 3: padding

cmd('im = impad;');
cmd('[ydim,xdim,zdim] = size( im )');
n = nextshot(n);                                   % 4: sizes after padding

cmd('[xramp,yramp] = meshgrid( [1:xdim]-xdim/2, [1:ydim]-ydim/2 );');
cmd('printf(''xramp: min %g, max %g\n'', min(xramp(:)), max(xramp(:)))');
cmd('printf(''yramp: min %g, max %g\n'', min(yramp(:)), max(yramp(:)))');
cmd('subplot(1,2,1); imagesc( xramp ); axis image; colorbar; title( ''Step 3: xramp (columns)'' );');
cmd('subplot(1,2,2); imagesc( yramp ); axis image; colorbar; title( ''Step 3: yramp (rows)'' );');
set(1, 'Position', [60 60 1100 520]);
n = nextshot(n);                                   % 5: coordinate grids

cmd('xramp = xramp / (xdim/2);');
cmd('yramp = yramp / (ydim/2);');
cmd('printf(''xramp: min %g, max %g\n'', min(xramp(:)), max(xramp(:)))');
cmd('printf(''yramp: min %g, max %g\n'', min(yramp(:)), max(yramp(:)))');
cmd('subplot(1,2,1); imagesc( xramp ); axis image; colorbar; title( ''Step 4: xramp normalized'' );');
cmd('subplot(1,2,2); imagesc( yramp ); axis image; colorbar; title( ''Step 4: yramp normalized'' );');
n = nextshot(n);                                   % 6: normalization

cmd('rad = sqrt( xramp.^2 + yramp.^2 );');
cmd('printf(''rad: min %g, max %g\n'', min(rad(:)), max(rad(:)))');
cmd('clf; imagesc( rad ); axis image; colorbar; title( ''Step 5: rad = distance to the image center'' );');
n = nextshot(n);                                   % 7: radius

cmd('K = -0.15');
cmd('fac = 1 + K*rad.^2;');
cmd('printf(''1+K*rad.^2: min %g, max %g\n'', min(fac(:)), max(fac(:)))');
cmd('clf; imagesc( fac ); axis image; colorbar; title( ''Step 6: factor 1 + K*rad^2, K = -0.15'' );');
n = nextshot(n);                                   % 8: scaling factor

cmd('xrampK = xramp .* (1 + K*rad.^2);');
cmd('yrampK = yramp .* (1 + K*rad.^2);');
cmd('subplot(1,2,1); imagesc( xrampK ); axis image; colorbar; title( ''Step 7: xrampK'' );');
cmd('subplot(1,2,2); imagesc( yrampK ); axis image; colorbar; title( ''Step 7: yrampK'' );');
n = nextshot(n);                                   % 9: new grid

cmd('imK = zeros( ydim, xdim, zdim );');
cmd('size( imK )');
n = nextshot(n);                                   % 10: empty result

chan = {'red', 'green', 'blue'};
for z = 1:3
  cmd(sprintf('imK(:,:,%d) = interp2( xramp, yramp, im(:,:,%d), xrampK, yrampK, ''cubic'' );', z, z));
  cmd(sprintf('clf; imagesc( imK(:,:,%d) ); axis image; colormap gray; colorbar; title( ''Step 8: interp2, %s channel'' );', z, chan{z}));
  n = nextshot(n);                                 % 11-13: channels
end

cmd('clf; imK(isnan(imK)) = 0; imshow( uint8([im imK]) ); title( ''Step 9: [padded original | corrected], K = -0.15'' );');
set(1, 'Position', [30 80 1500 420]);
n = nextshot(n);                                   % 14: result

% ---------------------------------------------------------------- PART 2: the function from the book with a slider
cmd('close all;');
Ks = [0 -0.05 -0.10 -0.15 -0.25 0.10 0.20];
for i = 1:numel(Ks)
  K = Ks(i);
  if i == 1
    cmd('lensdistort( ''monkey.png'' );');
  else
    cmd(sprintf('set( get( gcf, ''UserData'' ), ''Value'', %g );  %% move the slider', K));
    cmd('lensdistort( ''monkey.png'' );');
  end
  set(gcf, 'Position', [30 80 1500 460]);
  n = nextshot(n);                                 % 15-21: slider positions
end

% ---------------------------------------------------------------- PART 3: simulated barrel distortion and its correction
cmd('close all;');
cmd('lensdistort( ''monkey.png'' );');
cmd('set( get( gcf, ''UserData'' ), ''Value'', 0.20 );  % K = +0.20 makes a barrel-distorted copy');
cmd('lensdistort( ''monkey.png'' );');
set(gcf, 'Position', [30 80 1500 460]);
n = nextshot(n);
cmd('h = findobj( gca, ''type'', ''image'' );');
cmd('fr = get( h, ''cdata'' );');
cmd('imwrite( fr(:, size(fr,2)/2+1:end, :), ''monkey_barrel.png'' );');
cmd('ls');
n = nextshot(n);

cmd('close all;');
cmd('lensdistort( ''monkey_barrel.png'' );');
set(gcf, 'Position', [30 80 1500 460]);
n = nextshot(n);                                   % input = distorted photo, K = 0
Kc = [-0.10 -0.17 -0.25];
for i = 1:numel(Kc)
  cmd(sprintf('set( get( gcf, ''UserData'' ), ''Value'', %g );  %% move the slider', Kc(i)));
  cmd('lensdistort( ''monkey_barrel.png'' );');
  set(gcf, 'Position', [30 80 1500 460]);
  n = nextshot(n);
end
printf('\nDone: %d screenshots\n', n);
fid = fopen([getenv('SHOTDIR') '/stop.txt'], 'w'); fclose(fid);
