import { createContext, useContext } from "react";

export const AuthContext = createContext({
  user: null,
  loading: false,
  logout: async () => {},
});

export const useAuth = () => useContext(AuthContext);
