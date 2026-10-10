import { api } from './api';
import type { User } from '@/types/api';
import type { CreateUserInput } from '@/schemas/user.schema';

export const userService = {
  list: () => api.get<User[]>('/users'),
  create: (input: CreateUserInput) => api.post<User, CreateUserInput>('/users', input),
};
