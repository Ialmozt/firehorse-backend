// useManualOrder v3.0 - 2026 Production Hook
// Chakra UI Toast + Full Error Recovery

import { useCallback, useState } from 'react';
import { useToast } from '@chakra-ui/react';

export type FormData = {
  kworkid: string;
  topic: string;
};

export type SubmitResult = {
  success: boolean;
  orderid?: string;
  message: string;
};

export function useManualOrder() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  const submitOrder = useCallback(async (data: FormData): Promise<SubmitResult> => {
    const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
    const token = import.meta.env.VITE_INGRESS_SECRET;

    if (!token) {
      const msg = '❌ API token missing. Check VITE_INGRESS_SECRET in .env.local';
      toast({
        title: 'Ошибка',
        description: msg,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      return { success: false, message: msg };
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${apiUrl}/webhook`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Token': token,
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorText = await response.text();
        const msg = `HTTP ${response.status}: ${errorText.slice(0, 100)}`;
        toast({
          title: 'Ошибка',
          description: msg,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
        return { success: false, message: msg };
      }

      const result = await response.json() as { orderid: string; status: string; message: string };
      
      const successMsg = `✅ Order ${result.orderid} queued for AI processing`;
      toast({
        title: 'Успех',
        description: successMsg,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      return {
        success: true,
        orderid: result.orderid,
        message: successMsg,
      };
    } catch (error) {
      const msg = error instanceof Error 
        ? `Network error: ${error.message}`
        : 'Unknown submission error';
      
      toast({
        title: 'Ошибка сети',
        description: msg,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      return { success: false, message: msg };
    } finally {
      setIsSubmitting(false);
    }
  }, [toast]);

  return { submitOrder, isSubmitting };
}
