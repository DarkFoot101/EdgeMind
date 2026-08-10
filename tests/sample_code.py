// Assuming the original Python file contains imports and some functions

import { User } from './user';

class Good {
  user: User;

  constructor(user: User) {
    this.user = user;
  }

  greet(): void {
    console.log(`Hello, ${this.user.name}!`);
  }
}

// Example usage:
const user = new User('John Doe', 'john.doe@example.com');
const goodInstance = new Good(user);
goodInstance.greet();