% Оригинальный код MATLAB из книги H. Farid, "Digital Image Forensics",
% раздел 9.6 "Lens Distortion", стр. 158 (переписан с PDF без изменений логики;
% типографские кавычки заменены на обычные).
% Вызов: lensdistort('photo.png');  ползунок внизу слева задаёт K от -1 до 1.
function[imK] = lensdistort( filename )
if( isempty( get( gcf, 'UserData' ) ) )
  h = uicontrol; % GUI to control amount of lens distortion
  set( h, 'Style', 'slider' );
  set( h, 'Position', [20 20 200 20] );
  set( h, 'Value', 0, 'Min', -1, 'Max', 1 );
  set( h, 'SliderStep', [0.001 0.01] );
  set( h, 'Callback', sprintf( 'lensdistort(''%s'');', filename ) );
  set( gcf, 'UserData', h );
end
h = get( gcf, 'UserData' );
K = get( h, 'Value' );
% lens distortion
im = double( imread( filename ) );
[ydim,xdim,zdim] = size( im );
impad = zeros( ydim+100, xdim+100, zdim );
impad(51:ydim+50,51:xdim+50,:) = im; % pad with zeros
im = impad;                          % pad with zeros
[ydim,xdim,zdim] = size( im );
[xramp,yramp] = meshgrid( [1:xdim]-xdim/2, [1:ydim]-ydim/2 ); % image lattice
xramp = xramp / (xdim/2);            % normalize into [0,1]
yramp = yramp / (ydim/2);            % normalize into [0,1]
rad = sqrt( xramp.^2 + yramp.^2 );
xrampK = xramp .* (1 + K*rad.^2);    % new image lattice
yrampK = yramp .* (1 + K*rad.^2);    % new image lattice
imK = zeros( ydim, xdim, zdim );     % initialize new image
for z = 1 : zdim                     % remove lens distortion
  imK(:,:,z) = interp2( xramp, yramp, im(:,:,z), xrampK, yrampK, 'cubic' );
end
imshow( uint8([im imK]) );
title( K );
