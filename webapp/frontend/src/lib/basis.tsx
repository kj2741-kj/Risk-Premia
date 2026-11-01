import { createContext, useContext } from "react";

export interface BasisState {
  geometric: boolean;
  setGeometric: (g: boolean) => void;
}

export const BasisContext = createContext<BasisState>({ geometric: true, setGeometric: () => {} });
export const useBasis = () => useContext(BasisContext);
