function cmd(s)
  % prints the command as at the prompt, then runs it in the base workspace
  printf('>> %s\n', s);
  evalin('base', s);
end
