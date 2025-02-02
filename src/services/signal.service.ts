import { Injectable } from '@nestjs/common';
import { MessageBroker } from '../shared/message-broker';

@Injectable()
export class SignalService {
  private messageBroker: MessageBroker;

  constructor() {
    this.messageBroker = new MessageBroker();
    this.messageBroker.connect();
  }

  async processSignal(data: any) {
    // Process signal logic here
    const processedData = {
      ...data,
      processed: true,
      timestamp: new Date()
    };

    // Publish to other services
    await this.messageBroker.publishEvent(
      'signals',
      'signal.processed',
      processedData
    );

    return processedData;
  }
} 